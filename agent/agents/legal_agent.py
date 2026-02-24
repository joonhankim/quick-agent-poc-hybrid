"""
법률 RAG 에이전트 (LangGraph create_react_agent 기반)
legal_rag_crew.py 대체
"""
import hashlib
import re
import time
from typing import Dict, Tuple

from langgraph.prebuilt import create_react_agent

from agent.main import fast_llm
from agent.tools.azure_search_tool import azure_legal_search
from agent.agents.prompts import LEGAL_AGENT_SYSTEM_PROMPT
from api.core.logger import APILogger

logger = APILogger()

# 결과 캐시 (user_query 기준, TTL: 1시간)
_result_cache: Dict[str, Tuple[float, str]] = {}
_CACHE_TTL_SECONDS = 3600

_THOUGHT_PATTERN = re.compile(
    r"^(Thought:\s*|Action:\s*|Action Input:\s*|Observation:\s*)",
    re.MULTILINE,
)

_FALLBACK_RESPONSE = (
    "검색 결과에서 정확한 정보를 찾지 못했습니다. "
    "질문을 좀 더 구체적으로 작성해 주시면 더 나은 답변을 드릴 수 있습니다.\n\n"
    "※ 본 답변은 일반적인 법률 정보 제공 목적이며, "
    "구체적인 법률 문제는 변호사와 상담하시기 바랍니다."
)

# ReAct 에이전트 (모듈 레벨 싱글턴)
_legal_agent = create_react_agent(
    model=fast_llm,
    tools=[azure_legal_search],
    prompt=LEGAL_AGENT_SYSTEM_PROMPT,
)


def _sanitize_output(raw: str) -> str:
    """내부 Thought/Action 텍스트가 노출된 경우 정리"""
    if _THOUGHT_PATTERN.search(raw):
        logger.warning("에이전트 내부 reasoning 노출 감지, 폴백 응답 반환")
        return _FALLBACK_RESPONSE
    return raw


async def run_legal_agent(user_query: str) -> str:
    """
    법률 RAG 에이전트 실행
    동일한 user_query에 대해 1시간 TTL 인메모리 캐시 적용

    Args:
        user_query: 사용자의 법률 질문

    Returns:
        str: 법률 답변
    """
    # 캐시 확인
    cache_key = hashlib.md5(user_query.strip().encode()).hexdigest()
    if cache_key in _result_cache:
        cached_time, cached_result = _result_cache[cache_key]
        if time.time() - cached_time < _CACHE_TTL_SECONDS:
            logger.info(f"Legal Agent 결과 캐시 히트 - 쿼리: {user_query}")
            return cached_result
        else:
            del _result_cache[cache_key]

    try:
        logger.info(f"Legal Agent 실행 시작 - 쿼리: {user_query}")

        result = await _legal_agent.ainvoke(
            {"messages": [{"role": "user", "content": user_query}]}
        )

        # 마지막 AI 메시지에서 응답 추출
        ai_messages = [m for m in result["messages"] if m.type == "ai" and m.content]
        if ai_messages:
            response = ai_messages[-1].content
        else:
            response = _FALLBACK_RESPONSE

        response = _sanitize_output(response)
        logger.info("Legal Agent 실행 완료")

        # 캐시 저장
        _result_cache[cache_key] = (time.time(), response)

        return response

    except Exception as e:
        logger.error(f"Legal Agent 실행 중 오류 발생: {str(e)}")
        raise
