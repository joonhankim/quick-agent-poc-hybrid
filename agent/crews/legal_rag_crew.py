"""
법무지원 RAG 전문 에이전트 크루
Azure AI Search를 활용한 법률 문서 검색 및 분석
"""
import hashlib
import re
import time
from crewai import Agent, Task, Crew, Process, LLM
from typing import Optional, Dict, Tuple

from agent.tools.azure_search_tool import get_azure_search_tool
from api.core.logger import APILogger
from config.settings import get_config

logger = APILogger()

from agent.llm_endpoint import get_safe_llm

# Initialize LLM for CrewAI (gpt-4o: 빠른 응답 + 비-reasoning)
config = get_config()
llm = get_safe_llm("gpt-4o")._llm


def create_legal_rag_crew(user_query: str) -> Crew:
    """
    법무지원 RAG 전문 에이전트 크루 생성

    Args:
        user_query: 사용자의 법률 질문

    Returns:
        Crew: 법무 전문 크루 인스턴스
    """
    # Azure AI Search 도구 준비
    search_tool = get_azure_search_tool()

    # 단일 법률 어시스턴트 에이전트 (검색 + 분석 + 답변 통합)
    legal_assistant = Agent(
        role='법률 정보 어시스턴트',
        goal=f'"{user_query}"에 대해 법률 문서를 검색하고 500자 이내로 간결하게 답변',
        backstory="""법률 검색과 분석을 수행하는 AI 어시스턴트입니다.
        검색 도구로 관련 법령·판례를 찾고, 핵심만 간결하게 설명합니다.""",
        llm=llm,
        tools=[search_tool],
        max_iter=3,
        verbose=True,
        allow_delegation=False
    )

    # 단일 태스크: 검색 → 분석 → 답변 작성을 하나로 통합
    legal_task = Task(
        description=f"""다음 법률 질문에 답변하세요:

질문: {user_query}

수행 사항:
1. 검색 도구로 관련 법령·판례 검색
2. 검색 결과를 바탕으로 질문에 답변

답변 규칙:
- 700자 이내로 핵심만 간결하게 작성
- 답변 본문에서 관련 조항을 인용할 때 반드시 법령명과 조·항·호까지 명시 (예: 근로기준법 제23조 제1항)
- 답변 끝에 "📎 참고 법령" 섹션을 두고, 인용한 법령·판례를 목록으로 정리
- 마지막에 면책 조항 포함: "※ 본 답변은 일반적인 법률 정보 제공 목적이며, 구체적인 법률 문제는 변호사와 상담하시기 바랍니다."
""",
        agent=legal_assistant,
        expected_output='700자 이내의 간결한 법률 답변 (본문 내 조·항·호 인용, 참고 법령 목록, 면책 조항 포함)'
    )

    # 크루 생성 - 단일 에이전트, 단일 태스크
    crew = Crew(
        agents=[legal_assistant],
        tasks=[legal_task],
        process=Process.sequential,
        verbose=True,
    )

    logger.info(f"법무지원 RAG 크루 생성 완료 - 질문: {user_query}")
    return crew


# Crew 결과 캐시 (user_query 기준, TTL: 1시간)
_crew_result_cache: Dict[str, Tuple[float, str]] = {}
_CREW_CACHE_TTL_SECONDS = 3600


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


def _sanitize_crew_output(raw: str) -> str:
    """CrewAI 내부 Thought/Action 텍스트가 노출된 경우 정리"""
    if _THOUGHT_PATTERN.search(raw):
        logger.warning(f"CrewAI 내부 reasoning 노출 감지, 폴백 응답 반환")
        return _FALLBACK_RESPONSE
    return raw


def run_legal_rag_crew(user_query: str) -> str:
    """
    법무지원 RAG 크루를 실행하고 결과를 반환
    동일한 user_query에 대해 1시간 TTL 인메모리 캐시 적용

    Args:
        user_query: 사용자의 법률 질문

    Returns:
        str: 크루 실행 결과 (최종 법률 답변)
    """
    # 캐시 확인 (user_query 기준)
    cache_key = hashlib.md5(user_query.strip().encode()).hexdigest()
    if cache_key in _crew_result_cache:
        cached_time, cached_result = _crew_result_cache[cache_key]
        if time.time() - cached_time < _CREW_CACHE_TTL_SECONDS:
            logger.info(f"Crew 결과 캐시 히트 - 쿼리: {user_query}")
            return cached_result
        else:
            del _crew_result_cache[cache_key]

    try:
        crew = create_legal_rag_crew(user_query)
        result = crew.kickoff()
        result_str = _sanitize_crew_output(str(result))
        logger.info("법무지원 RAG 크루 실행 완료")

        # 캐시 저장
        _crew_result_cache[cache_key] = (time.time(), result_str)

        return result_str
    except Exception as e:
        logger.error(f"법무지원 RAG 크루 실행 중 오류 발생: {str(e)}")
        raise
