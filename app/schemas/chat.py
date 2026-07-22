from pydantic import BaseModel, Field
from typing import Optional, Any

class ChatRequest(BaseModel):
    prompt: str = Field(..., example="Find all contacts at decryptogen")
    action: Optional[str] = Field(None, example="search") # "search", "validate", "stats"

class ChatResponse(BaseModel):
    reply: str
    action_type: str = "text" # "search", "validate", "stats", "text"
    data: Optional[Any] = None
