"""
법무지원 RAG 전문 에이전트 크루
Azure AI Search를 활용한 법률 문서 검색 및 분석
"""
import hashlib
import time
from crewai import Agent, Task, Crew, Process, LLM
from typing import Optional, Dict, Tuple

from agent.tools.azure_search_tool import get_azure_search_tool
from api.core.logger import APILogger
from config.settings import get_config

logger = APILogger()

from agent.llm_endpoint import get_safe_llm

# Initialize LLM for CrewAI (config에서 모델명 로드)
config = get_config()
_model_name = config.get("AGENT_AZURE_OPENAI_MODEL_NAME", "gpt-5.1")
llm = get_safe_llm(_model_name)._llm


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

    # 1. 검색 전문가 에이전트
    search_specialist = Agent(
        role='법률 문서 검색 전문가',
        goal=f'{user_query}와 관련된 법률 문서, 판례, 법령을 정확하게 검색',
        backstory="""당신은 대형 로펌에서 15년간 법률 리서치를 담당한 전문가입니다.
        법률 용어, 조항 번호, 판례 번호를 정확히 이해하고,
        Azure AI Search를 활용하여 가장 관련성 높은 법률 문서를 찾아내는 데 탁월합니다.
        검색 결과의 품질을 평가하고 필요시 검색 쿼리를 개선할 수 있습니다.""",
        llm=llm,
        tools=[search_tool],
        verbose=True,
        allow_delegation=False
    )

    # 2. 법률 전문가 에이전트 (분석 + 작성 통합)
    legal_expert = Agent(
        role='법률 분석 및 답변 작성 전문가',
        goal='검색된 법률 문서를 분석하여 핵심 조항과 법적 해석을 제공하고, 일반인도 이해할 수 있는 명확한 한국어 답변을 작성',
        backstory="""당신은 사법연수원을 수석 졸업한 변호사로 20년간 다양한 법률 사건을 다뤘습니다.
        민법, 상법, 노동법, 행정법 등 전 분야에 걸친 깊은 이해를 가지고 있으며,
        복잡한 법률 문서에서 핵심 내용을 추출하고 명확한 법적 해석을 제공합니다.
        여러 법률 조항 간의 관계와 우선순위를 정확히 판단할 수 있습니다.
        또한 법률 전문 저널리스트 경험을 바탕으로 복잡한 법률 개념을
        일반인도 쉽게 이해할 수 있도록 설명하는 데 전문성을 가지고 있습니다.
        법적 정확성을 유지하면서도 친절하고 명확한 답변을 작성하며,
        반드시 참조 법령과 출처를 명시하고 법적 면책 조항을 포함합니다.""",
        llm=llm,
        verbose=True,
        allow_delegation=False
    )

    # 태스크 정의
    search_task = Task(
        description=f"""다음 법률 질문에 대해 관련 법률 문서를 검색하세요:

        질문: {user_query}

        수행 사항:
        1. 질문에서 핵심 법률 키워드 추출
        2. Azure AI Search를 사용하여 관련 법령, 판례, 실무 가이드 검색
        3. 검색 결과의 관련성 평가
        4. 가장 관련성 높은 문서 3-5개 선별

        출력: 선별된 문서의 제목, 출처, 핵심 내용 요약
        """,
        agent=search_specialist,
        expected_output='관련성 높은 법률 문서 목록 (제목, 출처, 요약 포함)'
    )

    combined_task = Task(
        description=f"""검색된 법률 문서를 분석하고, 사용자 친화적인 최종 답변을 작성하세요:

        질문: {user_query}

        [분석 단계]
        1. 검색된 각 문서의 핵심 조항 추출
        2. 질문과의 관련성 분석
        3. 적용 가능한 법률 원칙 설명
        4. 여러 문서 간 모순이 있다면 우선순위 판단
        5. 실무적 적용 방안 제시

        [답변 작성 단계]
        위 분석 결과를 바탕으로 다음 기준에 따라 최종 답변을 작성하세요:
        1. 명확하고 이해하기 쉬운 한국어 사용
        2. 사용자가 답변의 길이(예: 한 문장, 요약)나 형식을 지정한 경우 반드시 이를 최우선으로 준수
        3. 상세 설명은 사용자가 짧은 답변을 요청하지 않았을 때만 후속으로 배치
        4. 참조한 법령 조항과 판례를 명확히 표시
        5. 출처 정보 포함 (법령명, 조항 번호, 판례 번호 등)
        6. 다음 법적 면책 조항 필수 포함:
           "본 답변은 일반적인 법률 정보 제공을 목적으로 하며,
            개별 사안에 대한 법률 자문이 아닙니다.
            구체적인 법률 문제는 변호사와 상담하시기 바랍니다."

        출력: 최종 사용자 답변 (한국어, 정중한 톤, 출처 및 면책 조항 포함)
        """,
        agent=legal_expert,
        expected_output='사용자 친화적인 최종 법률 답변 (분석 내용, 출처 및 면책 조항 포함)'
    )

    # 태스크 완료 시 SSE status 이벤트 전송
    from agent.utils.callbacks import push_status

    _task_status_messages = [
        "법률 문서 검색 완료. 법률 분석 및 답변 작성을 시작합니다...",
    ]
    _task_step = {"count": 0}

    def _on_task_complete(task_output):
        idx = _task_step["count"]
        if idx < len(_task_status_messages):
            push_status(_task_status_messages[idx])
        _task_step["count"] += 1

    # 크루 생성 - 순차적 프로세스 (검색 → 분석+작성)
    crew = Crew(
        agents=[search_specialist, legal_expert],
        tasks=[search_task, combined_task],
        process=Process.sequential,
        verbose=True,
        task_callback=_on_task_complete,
    )

    logger.info(f"법무지원 RAG 크루 생성 완료 - 질문: {user_query}")
    return crew


# Crew 결과 캐시 (user_query 기준, TTL: 1시간)
_crew_result_cache: Dict[str, Tuple[float, str]] = {}
_CREW_CACHE_TTL_SECONDS = 3600


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
        result_str = str(result)
        logger.info("법무지원 RAG 크루 실행 완료")

        # 캐시 저장
        _crew_result_cache[cache_key] = (time.time(), result_str)

        return result_str
    except Exception as e:
        logger.error(f"법무지원 RAG 크루 실행 중 오류 발생: {str(e)}")
        raise
