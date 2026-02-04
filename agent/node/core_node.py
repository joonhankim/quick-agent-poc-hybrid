from langchain_core.messages import HumanMessage, SystemMessage
from agent.schema.state import AgentState
from agent.main import llm
from api.core.logger import APILogger

logger = APILogger()

import asyncio

def start_node(state: AgentState) -> AgentState:
    return state

# 기존 LLM 호출 노드 (사용하지 않지만 async 변환 예시로 둠)
async def generate_response_node(state: AgentState) -> AgentState:
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
    
    # [Async Refactoring] llm.ainvoke를 사용하여 비동기 호출
    response = await llm.ainvoke(messages)
    state.final_response = response.content
    return state


async def crew_collaboration_node(state: AgentState) -> AgentState:
    """
    법무지원 RAG 전문 에이전트 팀을 실행하는 노드
    LangGraph의 오케스트레이션 하에 CrewAI 법률 전문가 팀이 자율적으로 협업
    (Async Non-blocking 방식으로 실행)
    """
    from agent.crews.legal_rag_crew import run_legal_rag_crew
    
    logger.info(f"법무지원 RAG 크루 실행 시작 - 쿼리: {state.user_query}")
    
    try:
        # [Async Refactoring]
        # CrewAI의 run_legal_rag_crew는 동기 함수이므로, 
        # 메인 이벤트 루프를 차단하지 않기 위해 별도 스레드에서 실행합니다.
        crew_result = await asyncio.to_thread(run_legal_rag_crew, state.user_query)
        
        # 결과 처리 로직은 동일
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
        # ... 에러 처리 로직 유지 ...
        state.crew_metadata = {
            "crew_type": "legal_rag_crew",
            "status": "failed",
            "error": str(e)
        }
        # 폴백: 기존 LLM 응답 사용
        state.final_response = f"법무지원 RAG 크루 실행 중 오류가 발생했습니다. 기본 응답으로 전환합니다."
    
    return state


async def validation_node(state: AgentState) -> AgentState:
    """
    [FSM] 답변 품질 검증 노드
    - 답변에 불충분한 내용이나 에러 키워드가 있는지 검사
    - 실패 시 재시도 카운터 증가 및 사용자 친화적 메시지 추가
    """
    response = state.final_response or ""
    
    # 품질 검증 로직: 실패 키워드 체크
    failure_keywords = ["죄송합니다", "답변을 드릴 수 없습니다", "정보가 부족합니다", "오류가 발생"]
    
    is_valid = True
    for keyword in failure_keywords:
        if keyword in response:
            is_valid = False
            logger.warning(f"답변 품질 검증 실패: '{keyword}' 키워드 발견")
            break
    
    if is_valid:
        state.validation_status = "passed"
        logger.info("답변 품질 검증 통과")
    else:
        # 재시도 로직
        if state.retry_count < state.max_retries:
            state.retry_count += 1
            state.validation_status = "retry"
            
            # 사용자 친화적 메시지 (latency 우려 해소)
            retry_message = f"💡 더 나은 답변을 위해 재검토 중입니다... (시도 {state.retry_count}/{state.max_retries})"
            state.step_messages.append(retry_message)
            logger.info(f"재시도 진행 중: {state.retry_count}/{state.max_retries}")
        else:
            # 최대 재시도 초과
            state.validation_status = "failed"
            state.step_messages.append("⚠️ 최선을 다했으나 충분한 답변을 생성하지 못했습니다. 질문을 구체화해주시면 더 도움이 될 것 같습니다.")
            logger.warning(f"최대 재시도 횟수 초과: {state.max_retries}")
    
    return state