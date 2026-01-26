from pydantic import BaseModel
from typing import List, Dict, Any, Optional


class Identifiers(BaseModel):
    id: Optional[str] = None
    user_no: str
    chat_id: str
    room_id: str
 
class SystemInfo(BaseModel):
    model_name: Optional[str] = "gpt-5.2-chat-2"
    embedder_name: Optional[str] = "text-embedding-3-small"

class RuntimeInfo(BaseModel):
    user_query: Optional[str] = ""
    output: Optional[str] = ""
    intents: Optional[List] = []
    used_tools: Optional[List] = None
    top_k_tools: Optional[List] = []
    exe_date: Optional[str] = ""
    rag_document_ids: Optional[List[str]] = []
    chat_type: Optional[int] = 0
    metadata: Optional[Dict[str, Any]] = {}

class Models(BaseModel):
    identifiers: Identifiers
    system_info: SystemInfo
    runtime_info: RuntimeInfo
    search_data: Optional[Any] = None