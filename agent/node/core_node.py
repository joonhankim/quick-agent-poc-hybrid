from langchain_core.messages import HumanMessage, SystemMessage
from agent.schema.state import AgentState
from agent.main import llm, langchain_llm
from api.core.logger import APILogger

logger = APILogger()

import asyncio

def start_node(state: AgentState) -> AgentState:
    return state


async def router_node(state: AgentState) -> AgentState:
    """
    사용자의 질문 의도를 분석하여 라우팅 경로를 결정하는 노드
    - general: 일반적인 대화 (인사, 농담 등) -> general_chat_node로 이동
    - legal: 법률 관련 질문 -> crew_collaboration_node로 이동
    """
    query = state.user_query
    
    # 간단한 키워드 + LLM 기반 의도 분류
    # 1. 명확한 법률 키워드가 있으면 바로 legal로 분류 (Fast Path)
    legal_keywords = ["법", "조항", "판례", "소송", "형법", "민법", "상법", "위반", "처벌", "배상"]
    if any(keyword in query for keyword in legal_keywords):
        state.route = "legal"
        logger.info(f"라우팅 결정 (Keyword): legal - {query}")
        return state

    # 2. 그 외에는 LLM을 통해 의도 파악 (Slow Path but Accurate)
    try:
        system_prompt = """
        너는 사용자 질문의 의도를 분류하는 라우터야.
        질문이 '법률적 조언', '법적 지식', '판례 검색' 등 법과 관련된 내용이면 "legal"을,
        단순한 '인사', '일상 대화', '농담' 등 법과 무관한 내용이면 "general"을 출력해.
        오직 "legal" 또는 "general" 단어 하나만 응답해.
        """
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=query),
        ]
        
        response = await langchain_llm.ainvoke(messages)
        intent = response.content.strip().lower()
        
        if "legal" in intent:
            state.route = "legal"
        else:
            state.route = "general"
            
        logger.info(f"라우팅 결정 (LLM): {state.route} - {query}")
        
    except Exception as e:
        logger.error(f"라우팅 중 오류 발생: {e}, 기본값 legal로 진행")
        state.route = "legal"
        
    return state


async def general_chat_node(state: AgentState) -> AgentState:
    """
    일반적인 대화(General Chat)를 처리하는 노드
    - RAG나 도구 없이 LLM의 기본 지식으로 답변
    """
    query = state.user_query

    system_prompt = """
    너는 친절하고 도움을 주는 AI 어시스턴트야.
    사용자의 일상적인 질문이나 인사에 대해 자연스럽고 정중하게 한국어로 답변해줘.
    법률적인 조언이 필요한 질문이라고 판단되면, "저는 법률 전문가가 아니지만 일반적인 내용은 알려드릴 수 있습니다."라고 운을 떼고 답변해.
    하지만 되도록이면 가벼운 대화에 집중해.
    """

    # chat_context에서 최근 6개 메시지(3턴)만 추출하여 LangChain 메시지 객체로 직접 전달
    recent = list(state.chat_context)[-6:] if state.chat_context else []
    messages = [SystemMessage(content=system_prompt)] + recent + [HumanMessage(content=query)]
    
    try:
        logger.info(f"General Chat 생성 시작 - 쿼리: {query}")
        response = await langchain_llm.ainvoke(messages)
        state.final_response = response.content
        
        # 메타데이터 설정
        state.execution_metadata = {
            "node": "general_chat_node",
            "model": "gpt-4o" # or whatever config uses
        }
        
        # Validation Pass (일반 대화는 보통 검증 통과)
        state.validation_status = "passed" 
        
    except Exception as e:
        logger.error(f"General Chat 생성 실패: {e}")
        state.final_response = "죄송합니다. 잠시 오류가 발생하여 답변을 드릴 수 없습니다."
        state.validation_status = "failed"
        
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
    법무지원 RAG 에이전트를 실행하는 노드
    CrewAI 단일 Agent(gpt-4o) + Azure Search 도구로 법률 질문 처리
    """
    from agent.crews.legal_rag_crew import run_legal_rag_crew
    from agent.utils.callbacks import push_status

    logger.info(f"법무지원 RAG 크루 실행 시작 - 쿼리: {state.user_query}")
    push_status("법률 문서 검색 및 분석을 시작합니다...")

    try:
        crew_result = await asyncio.to_thread(run_legal_rag_crew, state.user_query)

        state.final_response = crew_result
        state.crew_metadata = {
            "crew_type": "legal_rag_crew",
            "status": "success",
            "query": state.user_query,
            "agents_used": ["legal_assistant"]
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
        state.final_response = "법률 질문 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."

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