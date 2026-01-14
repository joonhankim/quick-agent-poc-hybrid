from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import StreamingResponse
from typing import Dict, Any
from datetime import datetime
import asyncio

from agent.schema.chat import QueryRequest
from api.core.logger import APILogger
from agent.schema.state import AgentState
from agent.utils.formatter import create_sse_message
from agent.graph.core_graph import base_graph
from agent.utils.callbacks import AdvancedStateCallback


logger = APILogger()
router = APIRouter()


@router.post("/chat")
async def chat(request: QueryRequest, background_tasks: BackgroundTasks):
    """
    채팅 API 엔드포인트 (SSE 스트리밍)

    Args:
        request: 채팅 요청 (chat_id + 단일 메시지)

    Returns:
        StreamingResponse: SSE 형식의 스트리밍 응답
    """

    initial_state = AgentState(
        id=request.chat_id,
        chat_id=request.chat_id,
        user_no=request.user_no,
        room_id=request.room_id,
        user_query=request.user_query,
        exe_date=datetime.now().isoformat(),
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
        # 현재 이벤트 루프를 콜백에 전달
        event_loop = asyncio.get_running_loop()
        advanced_state_callback = AdvancedStateCallback(
            token_queue=token_queue,
            event_loop=event_loop
        )

        async def drain_tokens():
            """token_queue에서 토큰을 가져와 SSE 형식으로 변환하여 sse_queue에 전달"""
            try:
                while not done_flag.is_set():
                    try:
                        item = await asyncio.wait_for(
                            token_queue.get(), timeout=0.05
                        )
                        # item은 {"type": "content", "data": {"message": token}} 형태
                        if isinstance(item, dict):
                            item_type = item.get("type", "content")
                            item_data = item.get("data", {})
                            # content 타입이고 message가 있는 경우만 처리
                            if item_type == "content" and item_data.get("message"):
                                await sse_queue.put(
                                    create_sse_message("content", item_data.get("message"))
                                )
                    except asyncio.TimeoutError:
                        continue
            finally:
                # done_flag가 설정된 후 남은 토큰 처리
                while True:
                    try:
                        item = token_queue.get_nowait()
                        if isinstance(item, dict):
                            item_type = item.get("type", "content")
                            item_data = item.get("data", {})
                            if item_type == "content" and item_data.get("message"):
                                await sse_queue.put(
                                    create_sse_message("content", item_data.get("message"))
                                )
                    except asyncio.QueueEmpty:
                        break

        async def run_graph():
            try:
                await sse_queue.put(
                    create_sse_message("status", ">>> Graph workflow Start <<<")
                )

                # astream을 사용하여 비동기 스트리밍
                async for state in base_graph.astream(
                    initial_state,
                    stream_mode='values',
                    config={
                        'callbacks': [advanced_state_callback]
                    }
                ):
                    logger.debug(f">>>Graph 상태: {state}")
                    # state가 dict인 경우와 객체인 경우 모두 처리
                    if isinstance(state, dict):
                        step_messages = state.get("step_messages", [])
                        final_response = state.get("final_response")
                        final_response_metadata = state.get("final_response_metadata", {})
                    else:
                        step_messages = state.step_messages
                        final_response = state.final_response
                        final_response_metadata = getattr(state, "final_response_metadata", {})

                    if step_messages:
                        await sse_queue.put(
                            create_sse_message("status", step_messages[-1])
                        )
                    if final_response:
                        # 메타데이터와 함께 완료 메시지 전송
                        await sse_queue.put(
                            create_sse_message("complete", {
                                "message": final_response,
                                "metadata": final_response_metadata
                            })
                        )
                        response_data["content"] = final_response

                return advanced_state_callback.final_state

            except Exception as e:
                logger.error(f">>> Run Graph Error: {type(e).__name__}: {e}")
                await sse_queue.put(
                    create_sse_message("error", f"{type(e).__name__}: {str(e)}")
                )
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
                # Timeout은 정상 동작 - 큐가 비어있을 때 발생
                continue
            except asyncio.CancelledError:
                # Task가 취소된 경우
                logger.warning("SSE 스트리밍이 취소되었습니다")
                break
            except Exception as e:
                # 실제 에러만 로그 기록
                logger.error(f">>> Get SSE Queue Error: {type(e).__name__}: {e}")
                continue

        logger.info(f"SSE 스트리밍 완료 - 총 {message_count}개 메시지 전송")

        # Task 완료 대기
        result = await asyncio.gather(graph_task, drain_task, return_exceptions=True)
        graph_result = result[0]

        # Graph 실행 결과 로깅
        if isinstance(graph_result, Exception):
            logger.error(f"Graph 실행 실패: {type(graph_result).__name__}: {str(graph_result)}")
        elif graph_result:
            logger.info(f"채팅 요청 완료 - chat_id: {request.chat_id}, content: {request.user_query[:100]}...")

        completion_event.set()
#             background_tasks.add_task(
#                 save_conversation_after_streaming,
#                 request,
#                 response_data,
#                 completion_event,
#             )
    return StreamingResponse(
                deliver_chat_response_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                    "x-vercel-ai-data-stream": "v1",  # AI SDK 프로토콜 버전
                }
            )   


# async def save_conversation_after_streaming(
#     request: QueryRequest,
#     response_data: Dict[str, Any],
#     completion_event: asyncio.Event,
# ):
#     """스트리밍 완료 후 대화 저장"""

#     try:
#         await asyncio.wait_for(completion_event.wait(), timeout=30.0)
    
#     except Exception as e:
#         logger.error(
#             "\n>>>Streaming 완료 대기 시간이 초과하여 대화내역 저장 실패하였습니다.\n"
#         )
#         return

#     try:
#         # ChatHistoryManager를 사용하여 대화 저장
#         history_manager = ChatHistoryManager()

#         # final_state 형식으로 저장 데이터 구성
#         final_state = response_data.get("final_state", {})
#         if not final_state:
#             # final_state가 없으면 기본 정보로 구성
#             final_state = {
#                 "id": request.chat_id,
#                 "user_no": request.user_no,
#                 "chat_id": request.chat_id,
#                 "room_id": request.room_id,
#                 "user_query": request.user_query,
#                 "exe_date": request.exe_date,
#                 "intents": response_data.get("intents", []),
#                 "output": response_data.get("content", ""),
#                 "metadata": response_data.get("metadata", {}),
#                 "rag_document_ids": response_data.get("rag_document_ids", []),
#                 "chat_type": response_data.get("chat_type", 0),
#             }
#         else:
#             # final_state에 output 추가
#             final_state["output"] = response_data.get("content", "")

#         # 대화 저장
#         await history_manager.save_conversation(
#             chat_id=request.chat_id, final_state=final_state
#         )

#         logger.debug(f"대화 저장 완료: chat_id={request.chat_id}")

#     except Exception as e:
#         logger.error(f"대화 저장 실패: {e}")