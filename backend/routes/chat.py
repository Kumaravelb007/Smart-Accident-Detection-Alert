"""
Chat API Routes
Handles AI chatbot interactions.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from utils.ai_report import chat_with_ai

router = APIRouter(prefix="/api/chat", tags=["chat"])

class ChatRequest(BaseModel):
    message: str
    history: list = []

@router.post("/")
async def api_chat(request: ChatRequest):
    """Chat with the AI assistant."""
    try:
        reply = chat_with_ai(request.message, request.history)
        return {"reply": reply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
