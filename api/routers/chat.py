from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import StreamingResponse
from typing import Dict, Any
from datetime import datetime
import asyncio
import uuid

from agent.schema.chat import QueryRequest
from api.core.logger import APILogger
from agent.schema.state import AgentState
from agent.utils.formatter import (
    sse_start, sse_finish, sse_status, sse_error,
    sse_text_start, sse_text_delta, sse_text_end,
)
from agent.graph.core_graph import base_graph
from agent.utils.callbacks import AdvancedStateCallback, StatusNotifier, set_status_notifier
from agent.history_manager import ChatHistoryManager


logger = APILogger()
router = APIRouter()


@router.post("/chat")
async def chat(request: QueryRequest, background_tasks: BackgroundTasks):
    """
    채팅 API 엔드포인트 (SSE 스트리밍)
    Vercel AI SDK UI Message Stream 프로토콜 호환
    """

    # CosmosDB에서 최근 대화 히스토리 로드 (꼬리 질문 컨텍스트 유지)
    history_manager = ChatHistoryManager()
    recent_history = await asyncio.to_thread(
        history_manager.get_recent_conversation,
        user_no=request.user_no,
        room_id=request.room_id,
        max_turns=10,
    )
    logger.info(f"대화 히스토리 로드: {len(recent_history)}개 메시지")

    initial_state = AgentState(
        id=request.chat_id,
        chat_id=request.chat_id,
        user_no=request.user_no,
        room_id=request.room_id,
        user_query=request.user_query,
        exe_date=datetime.now().isoformat(),
        history=recent_history,
        final_response="",
        step_messages=[],
        route=None,
        retry_count=0,
        validation_status="pending",
        crew_metadata={},
        execution_metadata={},
        error_logs=[]
    )

    completion_event = asyncio.Event()

    response_data: Dict[str, Any] = {
        "content": "",
        "metadata": {},
        "final_state": None,
    }

    async def deliver_chat_response_stream():
        token_queue = asyncio.Queue()
        sse_queue = asyncio.Queue()
        done_flag = asyncio.Event()
        event_loop = asyncio.get_running_loop()

        # 텍스트 파트 ID (하나의 응답 메시지에 대해 고정)
        text_part_id = f"text-{uuid.uuid4().hex[:8]}"
        text_started = {"value": False}

        advanced_state_callback = AdvancedStateCallback(
            token_queue=token_queue,
            event_loop=event_loop
        )

        async def drain_tokens():
            """token_queue → Vercel AI SDK text-delta 변환 → sse_queue"""
            try:
                while not done_flag.is_set():
                    try:
                        item = await asyncio.wait_for(
                            token_queue.get(), timeout=0.05
                        )
                        if isinstance(item, dict):
                            item_type = item.get("type", "content")
                            item_data = item.get("data", {})
                            if item_type == "content" and item_data.get("message"):
                                token = item_data["message"]
                                # 첫 토큰이면 text-start 전송
                                if not text_started["value"]:
                                    await sse_queue.put(sse_text_start(text_part_id))
                                    text_started["value"] = True
                                await sse_queue.put(
                                    sse_text_delta(text_part_id, token)
                                )
                    except asyncio.TimeoutError:
                        continue
            finally:
                while True:
                    try:
                        item = token_queue.get_nowait()
                        if isinstance(item, dict):
                            item_type = item.get("type", "content")
                            item_data = item.get("data", {})
                            if item_type == "content" and item_data.get("message"):
                                token = item_data["message"]
                                if not text_started["value"]:
                                    await sse_queue.put(sse_text_start(text_part_id))
                                    text_started["value"] = True
                                await sse_queue.put(
                                    sse_text_delta(text_part_id, token)
                                )
                    except asyncio.QueueEmpty:
                        break

        async def run_graph():
            try:
                # StatusNotifier 설정 (crew 스레드에서도 SSE status push 가능)
                notifier = StatusNotifier(sse_queue=sse_queue, event_loop=event_loop)
                set_status_notifier(notifier)

                # ── 메시지 시작 ──
                await sse_queue.put(sse_start())
                await sse_queue.put(sse_status("질문을 분석하고 있습니다..."))

                async for state in base_graph.astream(
                    initial_state,
                    stream_mode='values',
                    config={
                        'callbacks': [advanced_state_callback],
                        'configurable': {'thread_id': request.room_id}
                    }
                ):
                    logger.debug(f">>>Graph 상태: {state}")
                    if isinstance(state, dict):
                        step_messages = state.get("step_messages", [])
                        final_response = state.get("final_response")
                    else:
                        step_messages = state.step_messages
                        final_response = state.final_response

                    # step_messages → data-status 이벤트
                    if step_messages:
                        await sse_queue.put(sse_status(step_messages[-1]))

                    # 최종 응답 처리
                    # - 콜백으로 토큰이 이미 스트리밍된 경우(text_started=True): DB 저장만
                    # - 콜백 없이 final_response만 있는 경우(text_started=False): SSE로 전송
                    if final_response:
                        response_data["content"] = final_response
                        if not text_started["value"]:
                            await sse_queue.put(sse_text_start(text_part_id))
                            text_started["value"] = True
                            await sse_queue.put(
                                sse_text_delta(text_part_id, final_response)
                            )

                # ── 텍스트 종료 + 메시지 완료 ──
                if text_started["value"]:
                    await sse_queue.put(sse_text_end(text_part_id))
                await sse_queue.put(sse_finish())

                return advanced_state_callback.final_state

            except Exception as e:
                logger.error(f">>> Run Graph Error: {type(e).__name__}: {e}")
                await sse_queue.put(sse_error(f"{type(e).__name__}: {str(e)}"))
                # 에러 시에도 finish 전송
                await sse_queue.put(sse_finish())
                raise

            finally:
                done_flag.set()

        graph_task = asyncio.create_task(run_graph())
        drain_task = asyncio.create_task(drain_tokens())

        # SSE 스트리밍 루프
        message_count = 0
        while not (done_flag.is_set() and sse_queue.empty()):
            try:
                item = await asyncio.wait_for(sse_queue.get(), timeout=0.1)
                message_count += 1
                logger.debug(f"SSE 메시지 전송 #{message_count}")
                logger.debug(f"SSE 메시지: {item}")
                yield item
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                logger.warning("SSE 스트리밍이 취소되었습니다")
                break
            except Exception as e:
                logger.error(f">>> Get SSE Queue Error: {type(e).__name__}: {e}")
                continue

        logger.info(f"SSE 스트리밍 완료 - 총 {message_count}개 메시지 전송")

        result = await asyncio.gather(graph_task, drain_task, return_exceptions=True)
        graph_result = result[0]

        if isinstance(graph_result, Exception):
            logger.error(f"Graph 실행 실패: {type(graph_result).__name__}: {str(graph_result)}")
        elif graph_result:
            logger.info(f"채팅 요청 완료 - chat_id: {request.chat_id}, content: {request.user_query[:100]}...")

        completion_event.set()

    background_tasks.add_task(
        save_conversation_after_streaming,
        request,
        response_data,
        completion_event,
    )

    return StreamingResponse(
        deliver_chat_response_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "x-vercel-ai-data-stream": "v1",
        }
    )


async def save_conversation_after_streaming(
    request: QueryRequest,
    response_data: Dict[str, Any],
    completion_event: asyncio.Event,
):
    """스트리밍 완료 후 대화 저장"""

    try:
        await asyncio.wait_for(completion_event.wait(), timeout=30.0)

    except Exception as e:
        logger.error(
            "\n>>>Streaming 완료 대기 시간이 초과하여 대화내역 저장 실패하였습니다.\n"
        )
        return

    try:
        from agent.main import model_name
        history_manager = ChatHistoryManager()

        final_state = response_data.get("final_state", {})
        if not final_state:
            final_state = {
                "id": request.chat_id,
                "user_no": request.user_no,
                "chat_id": request.chat_id,
                "room_id": request.room_id,
                "user_query": request.user_query,
                "exe_date": request.exe_date,
                "intents": response_data.get("intents", []),
                "output": response_data.get("content", ""),
                "metadata": response_data.get("metadata", {}),
                "rag_document_ids": response_data.get("rag_document_ids", []),
                "chat_type": response_data.get("chat_type", 0),
                "model_name": model_name,
            }
        else:
            final_state["output"] = response_data.get("content", "")
            if "model_name" not in final_state:
                final_state["model_name"] = model_name

        await history_manager.save_conversation(
            chat_id=request.chat_id, final_state=final_state
        )

        logger.debug(f"대화 저장 완료: chat_id={request.chat_id}")

    except Exception as e:
        logger.error(f"대화 저장 실패: {e}")
