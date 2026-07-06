"""
api/chat_routes.py — Routes cho chat streaming (SSE).
"""
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.app.services.chat_service import create_event_stream

router = APIRouter()


class ChatPayload(BaseModel):
    """Payload cho internal chat endpoint."""
    session_id: str
    question: str
    history_text: str
    section_title: str = None
    level: int = None


@router.post("/chat")
async def internal_chat(payload: ChatPayload):
    """Streaming chat qua RAG pipeline (SSE)."""
    async def stream():
        async for sse_string in create_event_stream(
            payload.session_id, 
            payload.question, 
            payload.history_text, 
            payload.section_title, 
            payload.level
        ):
            yield sse_string
    return StreamingResponse(stream(), media_type="text/event-stream")
