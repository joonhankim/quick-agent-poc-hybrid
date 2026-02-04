"""
CrewAI 기반 전문 에이전트 팀 정의
LangGraph 노드 내에서 호출되어 자율적으로 협업하는 에이전트 크루
"""
from crewai import Agent, Task, Crew, Process
from typing import Optional

from agent.main import llm
from api.core.logger import APILogger

logger = APILogger()


def create_research_crew(user_query: str) -> Crew:
    """
    리서치 전문 에이전트 크루 생성
    
    Args:
        user_query: 사용자 질문
        
    Returns:
        Crew: 리서치 전문 크루 인스턴스
    """
    # 1. 전문 리서치 에이전트 정의
    researcher = Agent(
        role='전문 리서치 분석가',
        goal=f'{user_query}에 대한 심층적이고 정확한 정보 수집 및 분석',
        backstory="""당신은 글로벌 컨설팅 펌에서 15년간 근무한 시니어 리서치 분석가입니다.
        복잡한 주제를 명확하게 분석하고, 신뢰할 수 있는 정보를 바탕으로 
        체계적인 보고서를 작성하는 것이 전문 분야입니다.""",
        llm=llm,
        verbose=True,
        allow_delegation=False
    )
    
    # 2. 에디터 에이전트 정의
    editor = Agent(
        role='시니어 콘텐츠 에디터',
        goal='리서치 결과를 사용자 친화적이고 명확한 한국어로 정리',
        backstory="""당신은 20년 경력의 전문 에디터로, 복잡한 기술 문서를 
        일반인도 이해할 수 있는 명확한 언어로 변환하는 데 탁월한 능력을 가지고 있습니다.""",
        llm=llm,
        verbose=True,
        allow_delegation=False
    )
    
    # 3. 태스크 정의
    research_task = Task(
        description=f"""다음 주제에 대해 심층 리서치를 수행하세요:
        
        주제: {user_query}
        
        요구사항:
        - 핵심 개념과 정의를 명확히 설명
        - 관련된 최신 트렌드나 사례 포함
        - 실용적인 인사이트 제공
        """,
        agent=researcher,
        expected_output='체계적으로 구조화된 리서치 보고서 (한국어)'
    )
    
    editing_task = Task(
        description=f"""리서치 결과를 검토하고 다음 기준에 맞게 편집하세요:
        
        - 명확하고 이해하기 쉬운 한국어 사용
        - 논리적인 흐름과 구조
        - 핵심 메시지가 명확히 전달되도록 정리
        - 정중하고 전문적인 톤 유지
        """,
        agent=editor,
        expected_output='최종 편집된 사용자 친화적 응답 (한국어)'
    )
    
    # 4. 크루 생성 및 반환
    crew = Crew(
        agents=[researcher, editor],
        tasks=[research_task, editing_task],
        process=Process.sequential,
        verbose=True
    )
    
    logger.info(f"CrewAI 리서치 크루 생성 완료 - 주제: {user_query}")
    return crew


def run_crew_research(user_query: str) -> str:
    """
    CrewAI 크루를 실행하고 결과를 반환
    
    Args:
        user_query: 사용자 질문
        
    Returns:
        str: 크루 실행 결과
    """
    try:
        crew = create_research_crew(user_query)
        result = crew.kickoff()
        logger.info("CrewAI 크루 실행 완료")
        return str(result)
    except Exception as e:
        logger.error(f"CrewAI 크루 실행 중 오류 발생: {str(e)}")
        raise
