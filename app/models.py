from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from datetime import datetime

class ChatType:
    GENERAL = "general"
    REALTIME = "realtime"

class Message(BaseModel):
    role: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)

class ChatSession(BaseModel):
    session_id: str
    chat_type: str
    messages: List[Message] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    chat_type: str = "general"
    use_search: bool = False

class ChatResponse(BaseModel):
    response: str
    session_id: str
    chat_type: str
    sources: Optional[List[Dict[str, str]]] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class VectorStoreStatus(BaseModel):
    loaded: bool
    document_count: int
    sources: List[str] = Field(default_factory=list)

class SystemStatus(BaseModel):
    vector_store: VectorStoreStatus
    groq_available: bool
    search_available: bool
    model_name: str
    active_sessions: int

class LearningDataItem(BaseModel):
    filename: str
    content: str
    char_count: int
