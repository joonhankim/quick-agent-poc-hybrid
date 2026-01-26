from typing import List, AsyncGenerator
import json
from uuid import uuid4
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from agent.schema.chat import Message
from api.core.logger import APILogger
from agent.llm_endpoint import get_safe_llm

logger = APILogger()


async def generate_sse_stream(messages: Message) -> AsyncGenerator[str, None]:
    """
    SSE(Server-Sent Events) 형식으로 스트리밍 응답 생성

    Args:
        messages: 채팅 메시지 목록

    Yields:
        SSE 형식의 문자열 데이터
    """
    try:
        # langchain_messages = []
        # for msg in messages:
        #     if msg.role == "user":
        #         langchain_messages.append(HumanMessage(content=msg.content))
        #     elif msg.role == "assistant":
        #         langchain_messages.append(AIMessage(content=msg.content))
        #     elif msg.role == "system":
        #         langchain_messages.append(SystemMessage(content=msg.content))

        # Azure OpenAI LLM 가져오기

        # 스트리밍 응답 생성
        full_response = ""
        message_id = f"assistant-{uuid4()}"

        # 메시지 시작 신호 전송
        yield f"data: {json.dumps({'type': 'start', 'messageId': message_id}, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'type': 'text-start', 'id': message_id}, ensure_ascii=False)}\n\n"
        
        async for chunk in llm.astream(langchain_messages):
            if hasattr(chunk, 'content') and chunk.content:
                content = chunk.content
                full_response += content

                # SSE 형식으로 데이터 전송
                sse_data = {
                    "type": "text-delta",
                    "id": message_id,
                    "delta": content
                }
                yield f"data: {json.dumps(sse_data, ensure_ascii=False)}\n\n"

        # 스트림 완료 신호
        yield f"data: {json.dumps({'type': 'text-end', 'id': message_id}, ensure_ascii=False)}\n\n"
        finish_data = {
            "type": "finish",
            "messageMetadata": {"finishReason": "stop"}
        }
        yield f"data: {json.dumps(finish_data, ensure_ascii=False)}\n\n"

        logger.info(f"채팅 응답 완료 - 응답 길이: {len(full_response)}")

    except Exception as e:
        logger.error(f"스트리밍 중 에러 발생: {e}")
        error_data = {
            "type": "error",
            "errorText": str(e)
        }
        yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"