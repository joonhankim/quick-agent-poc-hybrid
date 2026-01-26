from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import StreamingResponse
from typing import Dict, Any
from datetime import datetime
import asyncio

from agent.schema.chat import QueryRequest
from api.core.logger import APILogger
from agent.schema.state import AgentState
from agent.utils.formatter import create_sse_message
from agent.graph.core_graph import base_graph
from agent.utils.callbacks import AdvancedStateCallback
from agent.history_manager import ChatHistoryManager


logger = APILogger()
router = APIRouter()


@router.get("/get_room_history")
async def get_room_history(user_no: str, room_id: str):
    """
    방 내 대화 내역 조회
    """
    try:
        history_manager = ChatHistoryManager()
        room_history = history_manager.get_recent_conversation(user_no, room_id, max_turns=None)
        
        messages = []
        for message in room_history:
            messages.append({
                "role": "user" if message.type == "HumanMessage" else "assistant",
                "content": message.content,
            })
        return {
            "messages": messages,
        }
    except Exception as e:
        logger.error(f">>> Get Room History Error: {type(e).__name__}: {e}")
        return {"error": str(e)}