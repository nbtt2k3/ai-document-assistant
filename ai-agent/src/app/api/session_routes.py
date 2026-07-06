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
