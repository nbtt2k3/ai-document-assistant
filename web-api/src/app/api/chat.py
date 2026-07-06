import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import json
import os

from src.app.db.database import get_db
from src.app.models.session import Session as DBSession
from src.app.models.message import Message as DBMessage
from src.app.core.security import get_current_user_id
from src.app.schemas.chat import ChatRequest, SummarizeSectionRequest

router = APIRouter(prefix="/api/sessions", tags=["Chat"])

AI_AGENT_URL = os.getenv("AI_AGENT_URL", "http://ai-agent:8001")


def build_history_text(messages: list) -> str:
    if not messages:
        return ""
    lines = ["LỊCH SỬ HỘI THOẠI GẦN ĐÂY (để hiểu ngữ cảnh):"]
    for msg in messages:
        role_label = "👤 Bạn" if msg.role == "user" else "🤖 Bot"
        lines.append(f"{role_label}: {msg.content}")
    lines.append("")
    return "\n".join(lines) + "\n"


@router.post("/{session_id}/chat")
async def chat_endpoint(
    session_id: str,
    request: ChatRequest,
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

    if not request.question:
        raise HTTPException(status_code=400, detail="Question is required")

    is_system = request.question.startswith("[SYSTEM] ")
    actual_question = request.question.replace("[SYSTEM] ", "") if is_system else request.question

    if not is_system:
        user_msg = DBMessage(session_id=session_id, role="user", content=actual_question)
        db.add(user_msg)
        db.commit()

    from datetime import datetime
    bot_start_time = datetime.utcnow()

    history_msgs = (
        db.query(DBMessage)
        .filter(DBMessage.session_id == session_id)
        .order_by(DBMessage.created_at.asc())
        .all()[-10:]
    )
    history_text = build_history_text(history_msgs[:-1])

    async def wrapped_stream():
        payload = {
            "session_id": session_id,
            "question": actual_question,
            "history_text": history_text
        }
        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream("POST", f"{AI_AGENT_URL}/internal/chat", json=payload) as response:
                async for chunk in response.aiter_lines():
                    if chunk:
                        sse_string = chunk + "\n\n"
                        if '"_save_answer"' in sse_string:
                            try:
                                json_str = sse_string.replace("data: ", "").strip()
                                data = json.loads(json_str)
                                if data.get("type") == "_save_answer":
                                    bot_msg = DBMessage(
                                        session_id=session_id, 
                                        role="bot", 
                                        content=data["content"],
                                        created_at=bot_start_time
                                    )
                                    db.add(bot_msg)
                                    db.commit()
                            except Exception as e:
                                print(f"Error saving answer: {e}")
                            continue
                        
                        yield sse_string

    return StreamingResponse(wrapped_stream(), media_type="text/event-stream")


@router.post("/{session_id}/summarize_section")
async def summarize_section_endpoint(
    session_id: str,
    request: SummarizeSectionRequest,
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

    actual_question = f"Hãy tóm tắt chi tiết toàn bộ nội dung của phần/chương có tên là: '{request.section_title}'."

    async def wrapped_stream():
        payload = {
            "session_id": session_id,
            "question": actual_question,
            "history_text": "",
            "section_title": request.section_title,
            "level": request.level
        }
        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream("POST", f"{AI_AGENT_URL}/internal/chat", json=payload) as response:
                async for chunk in response.aiter_lines():
                    if chunk:
                        sse_string = chunk + "\n\n"
                        if '"_save_answer"' in sse_string:
                            continue
                        yield sse_string

    return StreamingResponse(wrapped_stream(), media_type="text/event-stream")
