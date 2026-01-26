from pydantic import BaseModel, Field
from datetime import datetime, timezone


class Message(BaseModel):
    role: str
    content: str


# class ChatRequest(BaseModel):
#     chat_id: str
#     message: Message

class QueryRequest(BaseModel):
    """하위 필수 항목은 모두 추후 request내에서 받도록 수정 필요"""
    user_query: str
    user_no: str
    chat_id: str
    room_id: str
    exe_date: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    )