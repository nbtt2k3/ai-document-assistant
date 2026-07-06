import os
import httpx
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
import uuid
from typing import List

from src.app.db.database import get_db
from src.app.models.session import Session as DBSession
from src.app.core.security import get_current_user_id
from src.app.schemas.session import SessionCreate, SessionUpdate, SessionResponse, MessageResponse

router = APIRouter(prefix="/api/sessions", tags=["Sessions"])

AI_AGENT_URL = os.getenv("AI_AGENT_URL", "http://ai-agent:8001")


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

@router.put("/{session_id}", response_model=SessionResponse)
def update_session(
    session_id: str,
    session_update: SessionUpdate,
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
    
    session.title = session_update.title
    db.commit()
    db.refresh(session)
    return session


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
    from src.app.models.message import Message as DBMessage
    messages = (
        db.query(DBMessage)
        .filter(DBMessage.session_id == session_id)
        .order_by(DBMessage.created_at.asc(), DBMessage.id.asc())
        .all()
    )
    return messages


@router.get("/{session_id}/toc")
async def get_table_of_contents(
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
        
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(f"{AI_AGENT_URL}/internal/toc/{session_id}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"toc": [], "error": str(e)}


@router.post("/{session_id}/upload")
async def upload_file(
    session_id: str,
    file: UploadFile = File(...),
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

    content = await file.read()

    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            files = {"file": (file.filename, content, file.content_type)}
            response = await client.post(
                f"{AI_AGENT_URL}/internal/ingest/{session_id}",
                files=files
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=response.text)
                
            data = response.json()
            num_segments = data.get("num_segments", 0)
            
            from src.app.models.message import Message as DBMessage
            upload_msg = DBMessage(session_id=session_id, role="user", content=f"**{file.filename}**")
            db.add(upload_msg)
            db.commit()
            
            return {"message": f"Đã xử lý thành công {num_segments} đoạn từ {file.filename}"}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Lỗi xử lý file từ AI Agent: {str(e)}")


@router.delete("/{session_id}")
async def delete_session(
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

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            await client.delete(f"{AI_AGENT_URL}/internal/session/{session_id}")
        except Exception as e:
            print(f"[WARNING] Could not delete data in AI Agent: {e}")

    db.delete(session)
    db.commit()

    return {"message": "Session deleted successfully"}
