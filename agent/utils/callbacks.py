from typing import Dict, Any
from langchain_core.callbacks.base import BaseCallbackHandler

from api.core.logger import APILogger

logger = APILogger()


class AdvancedStateCallback(BaseCallbackHandler):
    """
    AdvancedStateCallback is a callback handler for the advanced state of the agent.
    """
    def __init__(self, token_queue=None, event_loop=None):
        self.node_states = {}
        self.final_state = None
        self.token_queue = token_queue  # 토큰 스트리밍을 위한 큐
        self.event_loop = event_loop  # 이벤트 루프 참조

    def on_node_end(
        self, node_name: str, outputs: Dict[str, Any], **kwargs: Any
    ) -> None:
        """각 노드의 상태 저장"""
        self.node_states[node_name] = outputs

    def on_chain_end(self, outputs: Dict[str, Any], **kwargs: Any) -> None:
        """최종 상태와 모든 노드 상태 저장"""
        self.final_state = outputs

    def on_llm_start(
        self, serialized: Dict[str, Any], prompts: list[str], **kwargs: Any
    ) -> None:
        logger.debug(f"[CALLBACK] LLM 시작")

    def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        """새로운 토큰이 생성될 때마다 호출 (스트리밍)"""
        # 빈 토큰은 무시
        if not token:
            return
            
        logger.debug(f"[CALLBACK] New token: {token}")
        if self.token_queue and self.event_loop:
            # 비동기 큐에 토큰 추가 (딕셔너리 형태로 저장)
            # 동기 콜백에서 비동기 큐에 넣기 위해 run_coroutine_threadsafe 사용
            import asyncio
            try:
                # 기존 코드 스타일: {"type": "content", "data": {"message": token}} 형태
                token_item = {
                    "type": "content",
                    "data": {"message": token}
                }
                
                # 저장된 이벤트 루프에 코루틴 스케줄링
                asyncio.run_coroutine_threadsafe(
                    self.token_queue.put(token_item), self.event_loop
                )
            except Exception as e:
                logger.warning(f"토큰 큐에 추가 실패: {e}, token: {repr(token)}")
                pass

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        logger.debug(f"[CALLBACK] LLM 완료")