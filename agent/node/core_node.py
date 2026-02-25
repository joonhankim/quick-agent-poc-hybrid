import re

from langchain_core.messages import HumanMessage, SystemMessage
from agent.schema.state import AgentState
from agent.main import langchain_llm, fast_llm
from agent.agents.prompts import SUPERVISOR_PROMPT, GENERAL_CHAT_PROMPT
from api.core.logger import APILogger

logger = APILogger()


def start_node(state: AgentState) -> AgentState:
    return state


async def supervisor_node(state: AgentState) -> AgentState:
    """
    사용자의 질문 의도를 분석하여 라우팅 경로를 결정하는 노드
    - general: 일반적인 대화 (인사, 농담 등) -> general_chat_node
    - legal: 법률 관련 질문 -> legal_agent_node
    - research: 심층 분석/리서치 -> research_agent_node
    """
    query = state.user_query

    # 1. 명확한 법률 키워드가 있으면 바로 legal로 분류 (Fast Path)
    legal_keywords = ["법", "조항", "판례", "소송", "형법", "민법", "상법", "위반", "처벌", "배상"]
    if any(keyword in query for keyword in legal_keywords):
        state.route = "legal"
        logger.info(f"라우팅 결정 (Keyword): legal - {query}")
        return state

    # 2. 그 외에는 LLM을 통해 의도 파악 (Slow Path but Accurate)
    try:
        messages = [
            SystemMessage(content=SUPERVISOR_PROMPT),
            HumanMessage(content=query),
        ]

        response = await fast_llm.ainvoke(messages)
        intent = response.content.strip().lower()

        if "legal" in intent:
            state.route = "legal"
        elif "research" in intent:
            state.route = "research"
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
    RAG나 도구 없이 LLM의 기본 지식으로 답변
    """
    query = state.user_query

    # chat_context에서 최근 6개 메시지(3턴)만 추출
    recent = list(state.chat_context)[-6:] if state.chat_context else []
    messages = [SystemMessage(content=GENERAL_CHAT_PROMPT)] + recent + [HumanMessage(content=query)]

    try:
        logger.info(f"General Chat 생성 시작 - 쿼리: {query}")
        response = await fast_llm.ainvoke(messages)
        state.final_response = response.content

        state.execution_metadata = {
            "node": "general_chat_node",
            "model": "gpt-4o",
        }

        state.validation_status = "passed"

    except Exception as e:
        logger.error(f"General Chat 생성 실패: {e}")
        state.final_response = "죄송합니다. 잠시 오류가 발생하여 답변을 드릴 수 없습니다."
        state.validation_status = "failed"

    return state


async def legal_agent_node(state: AgentState) -> AgentState:
    """
    법률 RAG 에이전트를 실행하는 노드
    create_react_agent + azure_legal_search 도구로 법률 질문 처리
    """
    from agent.agents.legal_agent import run_legal_agent
    from agent.utils.callbacks import push_status

    logger.info(f"Legal Agent 실행 시작 - 쿼리: {state.user_query}")
    push_status("법률 문서 검색 및 분석을 시작합니다...")

    state.active_agent = "legal"

    # 최근 4개 메시지(2턴) 추출하여 대화 컨텍스트 전달
    recent_context = list(state.chat_context)[-4:] if state.chat_context else None

    try:
        result = await run_legal_agent(state.user_query, chat_context=recent_context)

        state.final_response = result
        state.agent_metadata = {
            "agent_type": "legal_react_agent",
            "status": "success",
            "query": state.user_query,
        }

        logger.info("Legal Agent 실행 완료")

    except Exception as e:
        logger.error(f"Legal Agent 실행 실패: {str(e)}")
        state.error_logs.append(f"Legal Agent execution error: {str(e)}")
        state.agent_metadata = {
            "agent_type": "legal_react_agent",
            "status": "failed",
            "error": str(e),
        }
        state.final_response = "법률 질문 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."

    return state


async def research_agent_node(state: AgentState) -> AgentState:
    """
    리서치 에이전트를 실행하는 노드
    2단계 LLM 체인 (researcher → editor)
    """
    from agent.agents.research_agent import run_research_agent
    from agent.utils.callbacks import push_status

    logger.info(f"Research Agent 실행 시작 - 쿼리: {state.user_query}")
    push_status("심층 리서치를 진행하고 있습니다...")

    state.active_agent = "research"

    try:
        result = await run_research_agent(state.user_query)

        state.final_response = result
        state.agent_metadata = {
            "agent_type": "research_chain",
            "status": "success",
            "query": state.user_query,
        }

        logger.info("Research Agent 실행 완료")

    except Exception as e:
        logger.error(f"Research Agent 실행 실패: {str(e)}")
        state.error_logs.append(f"Research Agent execution error: {str(e)}")
        state.agent_metadata = {
            "agent_type": "research_chain",
            "status": "failed",
            "error": str(e),
        }
        state.final_response = "리서치 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."

    return state


async def validation_node(state: AgentState) -> AgentState:
    """
    [FSM] 답변 품질 검증 노드
    - 답변에 불충분한 내용이나 에러 키워드가 있는지 검사
    - 실패 시 재시도 카운터 증가 및 사용자 친화적 메시지 추가
    """
    response = state.final_response or ""

    failure_keywords = ["죄송합니다", "답변을 드릴 수 없습니다", "정보가 부족합니다", "오류가 발생"]

    is_valid = True
    for keyword in failure_keywords:
        if keyword in response:
            is_valid = False
            logger.warning(f"답변 품질 검증 실패: '{keyword}' 키워드 발견")
            break

    # Legal 에이전트 추가 검증
    if is_valid and state.active_agent == "legal":
        if len(response) < 200:
            is_valid = False
            logger.warning(f"법률 답변 검증 실패: 최소 길이 미달 ({len(response)}자 < 200자)")
        elif "※" not in response and "면책" not in response and "법률 정보 제공 목적" not in response:
            is_valid = False
            logger.warning("법률 답변 검증 실패: 면책 조항 누락")
        elif not re.search(r"제\d+조", response):
            is_valid = False
            logger.warning("법률 답변 검증 실패: 법조항 인용 패턴(제N조) 없음")

    if is_valid:
        state.validation_status = "passed"
        logger.info("답변 품질 검증 통과")
    else:
        if state.retry_count < state.max_retries:
            state.retry_count += 1
            state.validation_status = "retry"

            retry_message = f"더 나은 답변을 위해 재검토 중입니다... (시도 {state.retry_count}/{state.max_retries})"
            state.step_messages.append(retry_message)
            logger.info(f"재시도 진행 중: {state.retry_count}/{state.max_retries}")
        else:
            state.validation_status = "failed"
            state.step_messages.append("최선을 다했으나 충분한 답변을 생성하지 못했습니다. 질문을 구체화해주시면 더 도움이 될 것 같습니다.")
            logger.warning(f"최대 재시도 횟수 초과: {state.max_retries}")

    return state
