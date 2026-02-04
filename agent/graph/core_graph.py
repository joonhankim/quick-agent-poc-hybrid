from typing import Any
from langgraph.graph import StateGraph, START, END

from agent.schema.state import AgentState
from agent.node.core_node import (
    start_node,
    generate_response_node,
    crew_collaboration_node,
)


def create_graph():
    """agent graph 생성 - LangGraph + CrewAI 하이브리드"""
    workflow = StateGraph(AgentState)
    
    # 노드 추가
    workflow.add_node("start_node", start_node)
    workflow.add_node("crew_collaboration", crew_collaboration_node)  # CrewAI 협업 노드
    
    # 엣지 연결 - LangGraph가 전체 흐름을 제어
    workflow.set_entry_point("start_node")
    workflow.add_edge("start_node", "crew_collaboration")
    workflow.add_edge("crew_collaboration", END)
    
    return workflow.compile()


base_graph = create_graph()