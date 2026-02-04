from typing import Any
from langgraph.graph import StateGraph, START, END

from agent.schema.state import AgentState
from agent.node.core_node import (
    start_node,
    generate_response_node,
    crew_collaboration_node,
    validation_node,
)


def should_retry(state: AgentState) -> str:
    """
    [FSM] 조건부 엣지: 검증 결과에 따라 재시도 여부 결정
    - retry: crew_collaboration 노드로 돌아가서 재시도
    - passed/failed: END로 이동
    """
    if state.validation_status == "retry":
        return "retry"
    else:
        # passed 또는 failed 모두 종료 (최종 응답은 이미 설정됨)
        return "end"


def create_graph():
    """
    agent graph 생성 - LangGraph + CrewAI 하이브리드 + FSM Retry Cycle
    """
    workflow = StateGraph(AgentState)
    
    # 노드 추가
    workflow.add_node("start_node", start_node)
    workflow.add_node("crew_collaboration", crew_collaboration_node)  # CrewAI 협업 노드
workflow.add_node("validation", validation_node)  # [FSM] 품질 검증 노드
    
    # 엣지 연결 - LangGraph가 전체 흐름을 제어
    workflow.set_entry_point("start_node")
    workflow.add_edge("start_node", "crew_collaboration")
    workflow.add_edge("crew_collaboration", "validation")
    
    # [FSM] 조건부 엣지: 검증 실패 시 재시도, 성공/최대 재시도 시 종료
    workflow.add_conditional_edges(
        "validation",
        should_retry,
        {
            "retry": "crew_collaboration",  # Cycle: 다시 협업 노드로
            "end": END
        }
    )
    
    return workflow.compile()


base_graph = create_graph()