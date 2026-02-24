"""
리서치 에이전트 (2단계 LLM 체인: researcher → editor)
research_crew.py 대체
"""
from langchain_core.messages import HumanMessage, SystemMessage

from agent.main import langchain_llm
from agent.agents.prompts import RESEARCHER_PROMPT, EDITOR_PROMPT
from api.core.logger import APILogger

logger = APILogger()


async def run_research_agent(user_query: str) -> str:
    """
    2단계 LLM 체인으로 리서치 수행 (도구 없이 순수 LLM 호출)

    Stage 1: researcher (langchain_llm) → 심층 리서치 보고서 작성
    Stage 2: editor (langchain_llm) → 사용자 친화적으로 편집

    Args:
        user_query: 사용자 질문

    Returns:
        str: 최종 편집된 리서치 응답
    """
    try:
        logger.info(f"Research Agent 실행 시작 - 쿼리: {user_query}")

        # Stage 1: Researcher
        researcher_messages = [
            SystemMessage(content=RESEARCHER_PROMPT),
            HumanMessage(content=user_query),
        ]
        research_result = await langchain_llm.ainvoke(researcher_messages)
        research_text = research_result.content
        logger.info("Research Agent Stage 1 (리서치) 완료")

        # Stage 2: Editor
        editor_messages = [
            SystemMessage(content=EDITOR_PROMPT),
            HumanMessage(content=f"다음 리서치 결과를 편집해주세요:\n\n{research_text}"),
        ]
        editor_result = await langchain_llm.ainvoke(editor_messages)
        final_text = editor_result.content
        logger.info("Research Agent Stage 2 (편집) 완료")

        return final_text

    except Exception as e:
        logger.error(f"Research Agent 실행 중 오류 발생: {str(e)}")
        raise
