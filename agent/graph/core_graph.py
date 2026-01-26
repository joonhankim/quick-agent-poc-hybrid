from typing import Any
from langgraph.graph import StateGraph, START, END

from agent.schema.state import AgentState
from agent.node.core_node import (
    start_node,
    generate_response_node,
)


def create_graph():
    """agent graph 생성"""
    workflow = StateGraph(AgentState)
    workflow.add_node("start_node", start_node)
    workflow.add_node("generate_response_node", generate_response_node)
    
    workflow.set_entry_point("start_node")
    workflow.add_edge("start_node", "generate_response_node")
    workflow.add_edge("generate_response_node", END)
    return workflow.compile()


base_graph = create_graph()