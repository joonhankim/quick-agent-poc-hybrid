from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.messages import messages_to_dict

from api.core.logger import APILogger
from agent.schema.state import AgentState
from agent.main import llm

logger = APILogger()

def start_node(state: AgentState) -> AgentState:
    return state

def generate_response_node(state: AgentState) -> AgentState:
    """
    Generate to final response node
    """
    history = state.history
    user_query = state.user_query
    system_prompt = """
정중하게 한국어로 대답해줘.
"""

    messages = [
        SystemMessage(content=system_prompt),
        SystemMessage(content=f"최근 대화 이력: {history}"),
        HumanMessage(content=user_query),
    ]
    # streaming=True로 설정되어 있으므로 invoke()를 사용해도
    # 콜백의 on_llm_new_token이 호출되어 스트리밍이 동작함
    response = llm.invoke(messages)
    state.final_response = response.content
    return state


def crew_collaboration_node(state: AgentState) -> AgentState:
    """
    법무지원 RAG 전문 에이전트 팀을 실행하는 노드
    LangGraph의 오케스트레이션 하에 CrewAI 법률 전문가 팀이 자율적으로 협업
    """
    from agent.crews.legal_rag_crew import run_legal_rag_crew
    
    logger.info(f"법무지원 RAG 크루 실행 시작 - 쿼리: {state.user_query}")
    
    try:
        # 법무지원 RAG 크루 실행
        crew_result = run_legal_rag_crew(state.user_query)
        
        # 결과를 상태에 저장
        state.final_response = crew_result
        state.crew_metadata = {
            "crew_type": "legal_rag_crew",
            "status": "success",
            "query": state.user_query,
            "agents_used": ["search_specialist", "legal_analyst", "legal_writer"]
        }
        
        logger.info("법무지원 RAG 크루 실행 완료")
        
    except Exception as e:
        logger.error(f"법무지원 RAG 크루 실행 실패: {str(e)}")
        state.error_logs.append(f"Legal RAG Crew execution error: {str(e)}")
        state.crew_metadata = {
            "crew_type": "legal_rag_crew",
            "status": "failed",
            "error": str(e)
        }
        # 폴백: 기존 LLM 응답 사용
        state.final_response = f"법무지원 RAG 크루 실행 중 오류가 발생했습니다. 기본 응답으로 전환합니다."
    
    return state