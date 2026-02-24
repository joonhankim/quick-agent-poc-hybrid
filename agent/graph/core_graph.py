from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from agent.schema.state import AgentState
from agent.node.core_node import (
    start_node,
    supervisor_node,
    general_chat_node,
    legal_agent_node,
    research_agent_node,
    validation_node,
)


def should_retry(state: AgentState) -> str:
    """
    [FSM] 조건부 엣지: 검증 결과에 따라 재시도 여부 결정
    - retry: active_agent 기반으로 해당 에이전트 노드로 돌아가서 재시도
    - passed/failed: END로 이동
    """
    if state.validation_status == "retry":
        # active_agent 기반 동적 라우팅
        if state.active_agent == "research":
            return "retry_research"
        return "retry_legal"
    else:
        return "end"


def route_decision(state: AgentState) -> str:
    """라우팅 결정 조건부 엣지"""
    if state.route == "general":
        return "general"
    elif state.route == "research":
        return "research"
    else:
        return "legal"


def create_graph():
    """
    agent graph 생성 - 순수 LangGraph Multi-Agent + FSM Retry Cycle + Persistence

    START → [start_node] → [supervisor_node] ─┬─ "general"  → [general_chat_node] → END
                                               ├─ "legal"    → [legal_agent_node] → [validation] ─┬─ "end" → END
                                               └─ "research" → [research_agent_node] → [validation]┘  │
                                                                    ↑                                   │
                                                                    └──────── "retry" ─────────────────┘
    """
    workflow = StateGraph(AgentState)

    # 노드 추가
    workflow.add_node("start_node", start_node)
    workflow.add_node("supervisor_node", supervisor_node)
    workflow.add_node("general_chat_node", general_chat_node)
    workflow.add_node("legal_agent_node", legal_agent_node)
    workflow.add_node("research_agent_node", research_agent_node)
    workflow.add_node("validation", validation_node)

    # 엣지 연결
    workflow.set_entry_point("start_node")
    workflow.add_edge("start_node", "supervisor_node")

    # 라우팅 조건부 엣지
    workflow.add_conditional_edges(
        "supervisor_node",
        route_decision,
        {
            "general": "general_chat_node",
            "legal": "legal_agent_node",
            "research": "research_agent_node",
        },
    )

    # General Chat은 바로 종료
    workflow.add_edge("general_chat_node", END)

    # Legal / Research → validation
    workflow.add_edge("legal_agent_node", "validation")
    workflow.add_edge("research_agent_node", "validation")

    # [FSM] 조건부 엣지: 검증 실패 시 active_agent 기반 재시도, 성공/최대 재시도 시 종료
    workflow.add_conditional_edges(
        "validation",
        should_retry,
        {
            "retry_legal": "legal_agent_node",
            "retry_research": "research_agent_node",
            "end": END,
        },
    )

    # [Persistence] 메모리 체크포인터 설정
    memory = MemorySaver()

    return workflow.compile(checkpointer=memory)


base_graph = create_graph()
