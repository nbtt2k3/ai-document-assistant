from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import json

from src.app.db.database import get_db
from src.app.models.session import Session as DBSession
from src.app.models.message import Message as DBMessage
from src.app.core.security import get_current_user_id
from src.app.schemas.chat import ChatRequest
from src.app.services.chat_service import build_history_text, create_event_stream

router = APIRouter(prefix="/api/sessions", tags=["Chat"])


@router.post("/{session_id}/chat")
async def chat_endpoint(
    session_id: str,
    request: ChatRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    # 1. Validate session
    session = (
        db.query(DBSession)
        .filter(DBSession.id == session_id, DBSession.user_id == user_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not request.question:
        raise HTTPException(status_code=400, detail="Question is required")

    # 2. Xử lý tin nhắn của user
    is_system = request.question.startswith("[SYSTEM] ")
    actual_question = request.question.replace("[SYSTEM] ", "") if is_system else request.question

    if not is_system:
        user_msg = DBMessage(session_id=session_id, role="user", content=actual_question)
        db.add(user_msg)
        db.commit()

    # 3. Lấy lịch sử hội thoại (delegate format cho chat_service)
    history_msgs = (
        db.query(DBMessage)
        .filter(DBMessage.session_id == session_id)
        .order_by(DBMessage.created_at.asc())
        .all()[-10:]
    )
    history_text = build_history_text(history_msgs[:-1])

    # 4. Stream wrapper để chặn event "_save_answer" và lưu DB
    async def wrapped_stream():
        async for sse_string in create_event_stream(session_id, actual_question, history_text):
            if '"_save_answer"' in sse_string:
                try:
                    # Trích xuất dữ liệu từ chuỗi SSE: "data: {...}\n\n"
                    json_str = sse_string.replace("data: ", "").strip()
                    data = json.loads(json_str)
                    if data.get("type") == "_save_answer":
                        bot_msg = DBMessage(
                            session_id=session_id, 
                            role="bot", 
                            content=data["content"]
                        )
                        db.add(bot_msg)
                        db.commit()
                except Exception as e:
                    print(f"Error saving answer: {e}")
                continue  # Bỏ qua không gửi event này về frontend

            yield sse_string

    return StreamingResponse(wrapped_stream(), media_type="text/event-stream")
