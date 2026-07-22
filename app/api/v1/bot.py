from fastapi import APIRouter, status
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.agent_brain import agent_brain

router = APIRouter(prefix="/chat", tags=["Agent Chat APIs"])

@router.post("", response_model=ChatResponse, status_code=status.HTTP_200_OK, summary="Process Agent Chat Prompt")
async def chat_with_agent(payload: ChatRequest):
    """Process user prompt, execute intent against Platform API, and return formatted Agent response."""
    result = await agent_brain.process_prompt(prompt=payload.prompt, action=payload.action)
    return ChatResponse(
        reply=result["reply"],
        action_type=result["action_type"],
        data=result["data"]
    )
