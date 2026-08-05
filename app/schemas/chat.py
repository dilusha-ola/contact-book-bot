from pydantic import BaseModel, Field
from typing import Optional, List, Any

class ChatRequest(BaseModel):
    prompt: str = Field(..., example="Find all contacts at decryptogen")
    action: Optional[str] = Field(None, example="search")
    session_id: Optional[str] = Field(None, example="session-1721812345")

class ChatResponse(BaseModel):
    reply: str
    action_type: str = "text"
    session_id: Optional[str] = None
    data: Optional[Any] = None

class SessionResponse(BaseModel):
    session_id: str
    title: str
    created_at: str
    updated_at: str

class UpdateSessionRequest(BaseModel):
    title: str = Field(..., example="Find Decryptogen Team")

class ChatMessageResponse(BaseModel):
    session_id: str
    role: str
    content: str
    timestamp: str
