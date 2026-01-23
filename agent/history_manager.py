from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from datetime import datetime, timezone
from typing import List, Dict, Any

from api.core.logger import APILogger
from agent.schema.db import (
    Identifiers,
    SystemInfo,
    RuntimeInfo,
    Models,
)
from agent.schema.search import SearchData
from db import chat_history_container

logger = APILogger()

class ChatHistoryManager:
    """Azure CosmosDB를 사용한 대화 히스토리 매니저"""

    def __init__(self):
        self.container = chat_history_container


    def _message_to_dict(self, message: BaseMessage) -> dict:
        """LangChain 메시지를 딕셔너리로 변환"""
        return {
            "type": message.__class__.__name__,
            "content": message.content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


    def _dict_to_message(self, message_dict: dict) -> BaseMessage:
        """딕셔너리를 LangChain 메시지로 변환"""
        message_type = message_dict["type"]
        content = message_dict["content"]

        if message_type == "HumanMessage":
            return HumanMessage(content=content)
        elif message_type == "AIMessage":
            return AIMessage(content=content)
        else:
            # 기본적으로 HumanMessage로 처리
            return HumanMessage(content=content)


    async def save_conversation(
        self,
        chat_id: str,
        final_state: dict = {},
    ):
        """
        대화 히스토리를 CosmosDB에 저장 (chat_id 기준)
        """
        save_data = conversation_memory_builder(**final_state).model_dump()
        save_data = {"id": save_data.get("identifiers").get("id"), **save_data}
        try:
            logger.info(f">>> Save Data: {save_data}")
            logger.info(f">>> Final State: {final_state}")
            logger.info(f">>> container: {self.container}")
            self.container.create_item(save_data, final_state.get("chat_id"))
            logger.debug(f">>> 대화 히스토리 저장 완료: {chat_id}")
        except Exception as e:
            logger.error(f"\n>>> 대화 히스토리 저장 실패: {e}")
            raise


    def get_recent_conversation(
        self, user_no: str, room_id: str, max_turns: int | None = 10
    ) -> List[HumanMessage | AIMessage]:
        """
        세션 내 최근 max_turns개의 대화를 LangChain 메시지로 반환

        Returns:
            LangChain 메시지 리스트 (Human → AI 순으로 구성)
        """
        try:
            query = """
            SELECT 
                c.runtime_info.user_query,
                c.runtime_info.output
            FROM c
            WHERE c.identifiers.user_no = @user_no AND c.identifiers.room_id = @room_id
            ORDER BY c._ts DESC
            """
            logger.info(f">>> Query: {query}")
            
            parameters: List[Dict[str, Any]] = [
                {"name": "@user_no", "value": user_no},
                {"name": "@room_id", "value": room_id},
            ]
            if max_turns is not None:
                parameters.append({"name": "@limit", "value": max_turns})
                query += " OFFSET 0 LIMIT @limit"
            logger.info(f">>> Parameters: {parameters}")
            results = list(
                self.container.query_items(
                    query=query,
                    parameters=parameters,
                    enable_cross_partition_query=True,
                )
            )

            # 최신순이므로 역순 정렬
            results.reverse()
            logger.info(f">>> 야후Results: {results}")
            messages = []
            for r in results:
                user_query = r.get("user_query")
                output = r.get("output")
                if user_query:
                    messages.append(HumanMessage(content=user_query))
                if output:
                    messages.append(AIMessage(content=output))

            return messages

        except Exception as e:
            logger.error(f"\n>>> [get_recent_conversation] 최근 대화 로딩 실패: {e}")
            logger.error(f">>> Request Parameters: {user_no} / {room_id} / {max_turns}")
            return []


def conversation_memory_builder(**kwargs):
    # 식별 정보
    identifiers = Identifiers(
        id=kwargs.get("chat_id"),
        user_no=kwargs.get("user_no"),
        chat_id=kwargs.get("chat_id"),
        room_id=kwargs.get("room_id"),
    )

    # 시스템 정보
    system_info = SystemInfo(
        model_name=kwargs.get("model_name", "gpt-5"),
        embedder_name=kwargs.get("embedder_name", "text-embedding-3-small"),
    )

    # 실행 정보
    runtime_config = RuntimeInfo(
        user_query=kwargs.get("user_query"),
        output=kwargs.get("output", ""),
        intents=kwargs.get("intents", []),
        used_tools=kwargs.get("used_tools"),
        top_k_tools=kwargs.get("top_k_tools", []),
        exe_date=kwargs.get("exe_date"),
        rag_document_ids=kwargs.get("rag_document_ids", []),
        chat_type=kwargs.get("chat_type", 0),
    )

    # 검색 결과 데이터
    retrieval_data = SearchData(
        origin_query=kwargs.get("retrieval_result", {}).get("original_query", ""),
        sub_queries=kwargs.get("retrieval_result", {}).get("sub_queries", []),
    )

    return Models(
        identifiers=identifiers,
        system_info=system_info,
        runtime_info=runtime_config,
        search_data=retrieval_data,
    )
