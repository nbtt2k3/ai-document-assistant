from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
import uuid
from typing import List

from src.app.db.database import get_db
from src.app.models.session import Session as DBSession
from src.app.models.message import Message as DBMessage
from src.app.core.security import get_current_user_id
from src.app.schemas.session import SessionCreate, SessionResponse, MessageResponse
from src.app.services.document_service import (
    get_supported_extensions,
    save_upload_file,
    process_upload,
    cleanup_session_data,
)

router = APIRouter(prefix="/api/sessions", tags=["Sessions"])


@router.get("/", response_model=List[SessionResponse])
def get_all_sessions(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    sessions = (
        db.query(DBSession)
        .filter(DBSession.user_id == user_id)
        .order_by(DBSession.created_at.desc())
        .all()
    )
    return sessions


@router.post("/", response_model=SessionResponse)
def create_session(
    session: SessionCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    new_session_id = str(uuid.uuid4())
    new_session = DBSession(id=new_session_id, user_id=user_id, title=session.title)
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return new_session


@router.get("/{session_id}/messages", response_model=List[MessageResponse])
def get_session_messages(
    session_id: str,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    session = (
        db.query(DBSession)
        .filter(DBSession.id == session_id, DBSession.user_id == user_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session.messages


@router.post("/{session_id}/upload")
async def upload_file(
    session_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    # 1. Validate session ownership
    session = (
        db.query(DBSession)
        .filter(DBSession.id == session_id, DBSession.user_id == user_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # 2. Validate file extension
    from pathlib import Path
    ext = Path(file.filename).suffix.lower()
    if ext not in get_supported_extensions():
        raise HTTPException(
            status_code=400,
            detail=f"Định dạng '{ext}' không được hỗ trợ. "
                   f"Hỗ trợ: {', '.join(sorted(get_supported_extensions()))}"
        )

    # 3. Lưu file + parse + index (delegate cho document_service)
    content = await file.read()
    file_path = save_upload_file(session_id, file.filename, content)

    try:
        num_segments = process_upload(session_id, file_path, file.filename)
        return {"message": f"Đã xử lý thành công {num_segments} đoạn từ {file.filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý file: {str(e)}")


@router.delete("/{session_id}")
def delete_session(
    session_id: str,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    session = (
        db.query(DBSession)
        .filter(DBSession.id == session_id, DBSession.user_id == user_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # 1. Dọn dẹp file, vectorstore, BM25 (delegate cho document_service)
    cleanup_session_data(session_id)

    # 2. Xoá session khỏi SQL (cascade xoá messages tự động)
    db.delete(session)
    db.commit()

    return {"message": "Session deleted successfully"}
