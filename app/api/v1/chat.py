from datetime import datetime
from fastapi import APIRouter, HTTPException, status
from typing import List, Optional
from app.schemas.chat import ChatRequest, ChatResponse, SessionResponse, UpdateSessionRequest, ChatMessageResponse
from app.services.agent_brain import agent_brain
from app.services.platform_client import platform_client
from app.repositories.chat_repo import chat_repo

router = APIRouter(prefix="/chat", tags=["Agent Chat & History APIs"])

@router.get("/token", summary="Inspect Active MudraID Bearer Access Token")
async def get_mudraid_token():
    """Retrieve and inspect the current signed MudraID Bearer Access Token negotiated with MudraID."""
    return platform_client.get_active_token()

@router.post("", response_model=ChatResponse, status_code=status.HTTP_200_OK, summary="Process Agent Chat Prompt")
async def chat_with_agent(payload: ChatRequest):
    """Process user prompt, persist messages to MongoDB Atlas, and return Agent response."""
    session_id = payload.session_id or f"session-{int(datetime.now().timestamp())}"

    # 1. Save user message to MongoDB
    await chat_repo.add_message(session_id=session_id, role="user", content=payload.prompt)

    # 2. Process via LangChain / LLM
    result = await agent_brain.process_prompt(prompt=payload.prompt, action=payload.action)
    reply = result["reply"]

    # 3. Save assistant response to MongoDB
    await chat_repo.add_message(session_id=session_id, role="assistant", content=reply)

    return ChatResponse(
        reply=reply,
        action_type=result.get("action_type", "text"),
        session_id=session_id,
        error_code=result.get("error_code"),
        data=result.get("data")
    )

@router.get("/sessions", response_model=List[SessionResponse], summary="List Chat Sessions")
async def list_chat_sessions():
    """Retrieve all chat sessions stored in MongoDB Atlas."""
    return await chat_repo.get_all_sessions()

@router.put("/sessions/{session_id}", response_model=SessionResponse, summary="Rename Chat Session Title")
async def update_chat_session(session_id: str, payload: UpdateSessionRequest):
    """Rename a chat session title in MongoDB Atlas."""
    updated = await chat_repo.update_session_title(session_id, payload.title)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    return updated

@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessageResponse], summary="Get Session History")
async def get_session_messages(session_id: str):
    """Retrieve full conversation history for a chat session."""
    return await chat_repo.get_session_messages(session_id)

@router.delete("/sessions/{session_id}", status_code=status.HTTP_200_OK, summary="Delete Chat Session")
async def delete_chat_session(session_id: str):
    """Delete a chat session and all associated messages from MongoDB Atlas."""
    await chat_repo.delete_session(session_id)
    return {"message": f"Session '{session_id}' successfully deleted"}
