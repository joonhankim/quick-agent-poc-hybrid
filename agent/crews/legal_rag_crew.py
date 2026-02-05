"""
법무지원 RAG 전문 에이전트 크루
Azure AI Search를 활용한 법률 문서 검색 및 분석
"""
from crewai import Agent, Task, Crew, Process, LLM
from typing import Optional

from agent.tools.azure_search_tool import get_azure_search_tool
from api.core.logger import APILogger
from config.settings import get_config

logger = APILogger()

from agent.llm_endpoint import get_safe_llm

# Initialize GPT-4o LLM for CrewAI
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
    
    # 2. 법률 분석가 에이전트
    legal_analyst = Agent(
        role='법률 분석 전문가',
        goal='검색된 법률 문서를 분석하여 핵심 조항과 법적 해석 제공',
        backstory="""당신은 사법연수원을 수석 졸업한 변호사로 20년간 다양한 법률 사건을 다뤘습니다.
        민법, 상법, 노동법, 행정법 등 전 분야에 걸친 깊은 이해를 가지고 있으며,
        복잡한 법률 문서에서 핵심 내용을 추출하고 명확한 법적 해석을 제공합니다.
        여러 법률 조항 간의 관계와 우선순위를 정확히 판단할 수 있습니다.""",
        llm=llm,
        verbose=True,
        allow_delegation=False
    )
    
    # 3. 법률 답변 작성자 에이전트
    legal_writer = Agent(
        role='법률 답변 작성 전문가',
        goal='법률 분석 결과를 일반인도 이해할 수 있는 명확한 한국어로 작성',
        backstory="""당신은 법률 전문 저널리스트 출신으로 복잡한 법률 개념을
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
    
    analysis_task = Task(
        description=f"""검색된 법률 문서를 분석하여 질문에 대한 법적 해석을 제공하세요:
        
        질문: {user_query}
        
        수행 사항:
        1. 검색된 각 문서의 핵심 조항 추출
        2. 질문과의 관련성 분석
        3. 적용 가능한 법률 원칙 설명
        4. 여러 문서 간 모순이 있다면 우선순위 판단
        5. 실무적 적용 방안 제시
        
        출력: 체계적인 법률 분석 보고서
        """,
        agent=legal_analyst,
        expected_output='법률 분석 보고서 (핵심 조항, 법적 해석, 적용 방안 포함)'
    )
    
    writing_task = Task(
        description=f"""법률 분석 결과를 바탕으로 사용자 친화적인 답변을 작성하세요:
        
        질문: {user_query}
        
        작성 기준:
        1. 명확하고 이해하기 쉬운 한국어 사용
        2. 핵심 답변을 먼저 제시하고 상세 설명은 후속으로 배치
        3. 참조한 법령 조항과 판례를 명확히 표시
        4. 출처 정보 포함 (법령명, 조항 번호, 판례 번호 등)
        5. 다음 법적 면책 조항 필수 포함:
           "본 답변은 일반적인 법률 정보 제공을 목적으로 하며, 
            개별 사안에 대한 법률 자문이 아닙니다. 
            구체적인 법률 문제는 변호사와 상담하시기 바랍니다."
        
        출력: 최종 사용자 답변 (한국어, 정중한 톤)
        """,
        agent=legal_writer,
        expected_output='사용자 친화적인 최종 법률 답변 (출처 및 면책 조항 포함)'
    )
    
    # 크루 생성 - 순차적 프로세스 (검색 → 분석 → 작성)
    crew = Crew(
        agents=[search_specialist, legal_analyst, legal_writer],
        tasks=[search_task, analysis_task, writing_task],
        process=Process.sequential,
        verbose=True
    )
    
    logger.info(f"법무지원 RAG 크루 생성 완료 - 질문: {user_query}")
    return crew


def run_legal_rag_crew(user_query: str) -> str:
    """
    법무지원 RAG 크루를 실행하고 결과를 반환
    
    Args:
        user_query: 사용자의 법률 질문
        
    Returns:
        str: 크루 실행 결과 (최종 법률 답변)
    """
    try:
        crew = create_legal_rag_crew(user_query)
        result = crew.kickoff()
        logger.info("법무지원 RAG 크루 실행 완료")
        return str(result)
    except Exception as e:
        logger.error(f"법무지원 RAG 크루 실행 중 오류 발생: {str(e)}")
        raise
