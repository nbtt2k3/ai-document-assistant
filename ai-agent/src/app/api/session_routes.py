"""
api/session_routes.py — Routes cho quản lý session.
"""
from fastapi import APIRouter

from src.app.services.document_service import cleanup_session_data

router = APIRouter()


@router.delete("/session/{session_id}")
async def internal_delete_session(session_id: str):
    """Dọn dẹp toàn bộ dữ liệu của một session."""
    cleanup_session_data(session_id)
    return {"status": "ok"}


from pydantic import BaseModel
from src.app.services.chat_service import summarize_memory

class SummarizeMemoryPayload(BaseModel):
    old_summary: str
    new_messages: str

@router.post("/summarize_memory")
async def internal_summarize_memory(payload: SummarizeMemoryPayload):
    """Tóm tắt lịch sử hội thoại (gọi từ web-api)."""
    try:
        new_summary = summarize_memory(payload.old_summary, payload.new_messages)
        return {"new_summary": new_summary}
    except Exception as e:
        return {"error": str(e)}
