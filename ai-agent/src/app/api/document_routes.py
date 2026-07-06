"""
api/document_routes.py — Routes cho upload tài liệu và Table of Contents.
"""
from fastapi import APIRouter, HTTPException, UploadFile, File
from pathlib import Path

from src.app.services.document_service import (
    save_upload_file,
    process_upload,
    get_supported_extensions,
    get_toc_for_session,
)

router = APIRouter()


@router.post("/ingest/{session_id}")
async def internal_ingest(session_id: str, file: UploadFile = File(...)):
    """Upload và index tài liệu vào RAG engine."""
    ext = Path(file.filename).suffix.lower()
    if ext not in get_supported_extensions():
        raise HTTPException(
            status_code=400,
            detail=f"Định dạng '{ext}' không được hỗ trợ."
        )

    content = await file.read()
    file_path = save_upload_file(session_id, file.filename, content)

    try:
        num_segments = process_upload(session_id, file_path, file.filename)
        return {"num_segments": num_segments}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/toc/{session_id}")
async def internal_toc(session_id: str):
    """Lấy Table of Contents từ tài liệu đã upload."""
    try:
        toc = get_toc_for_session(session_id)
        return {"toc": toc}
    except Exception as e:
        return {"toc": [], "error": str(e)}
