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