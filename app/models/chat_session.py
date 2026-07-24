from pydantic import BaseModel, Field
from typing import Optional

class ChatSessionModel(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    session_id: str = Field(..., description="Unique chat session identifier")
    title: str = Field(..., description="Title of the chat session")
    created_at: Optional[str] = Field(None, description="Session creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last updated timestamp")

    class Config:
        populate_by_name = True
