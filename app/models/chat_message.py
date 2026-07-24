from pydantic import BaseModel, Field
from typing import Optional

class ChatMessageModel(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    session_id: str = Field(..., description="Associated chat session ID")
    role: str = Field(..., description="Role of message sender ('user' or 'assistant')")
    content: str = Field(..., description="Message text content")
    timestamp: Optional[str] = Field(None, description="Message timestamp")

    class Config:
        populate_by_name = True
