import httpx
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import json
import os

from src.app.db.database import get_db, SessionLocal
from src.app.models.session import Session as DBSession
from src.app.models.message import Message as DBMessage
from src.app.core.security import get_current_user_id
from src.app.schemas.chat import ChatRequest, SummarizeSectionRequest
from src.app.core.rate_limit import limiter

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

async def summarize_memory_task(session_id: str):
    """Background task: tự động tóm tắt tin nhắn cũ nếu quá dài."""
    db = SessionLocal()
    try:
        session = db.query(DBSession).filter(DBSession.id == session_id).first()
        if not session:
            return

        unsummarized_msgs = (
            db.query(DBMessage)
            .filter(DBMessage.session_id == session_id, DBMessage.is_summarized == False)
            .order_by(DBMessage.created_at.asc())
            .all()
        )

        # Nếu có hơn 6 tin nhắn chưa tóm tắt (tương đương 3 lượt hỏi-đáp)
        if len(unsummarized_msgs) > 6:
            new_messages_text = build_history_text(unsummarized_msgs)
            payload = {
                "old_summary": session.summary or "",
                "new_messages": new_messages_text
            }
            async with httpx.AsyncClient(timeout=None) as client:
                resp = await client.post(f"{AI_AGENT_URL}/internal/summarize_memory", json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    if "new_summary" in data:
                        session.summary = data["new_summary"]
                        for msg in unsummarized_msgs:
                            msg.is_summarized = True
                        db.commit()
                        print(f"[Memory] Đã tóm tắt session {session_id}")
    except Exception as e:
        print(f"[Memory] Error in summarize_memory_task: {e}")
    finally:
        db.close()


@router.post("/{session_id}/chat")
@limiter.limit("20/minute")
async def chat_endpoint(
    request: Request,
    session_id: str,
    payload: ChatRequest,
    background_tasks: BackgroundTasks,
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

    if not payload.question:
        raise HTTPException(status_code=400, detail="Question is required")

    is_system = payload.question.startswith("[SYSTEM] ")
    actual_question = payload.question.replace("[SYSTEM] ", "") if is_system else payload.question

    if not is_system:
        user_msg = DBMessage(session_id=session_id, role="user", content=actual_question)
        db.add(user_msg)
        db.commit()

    from datetime import datetime
    bot_start_time = datetime.utcnow()

    unsummarized_msgs = (
        db.query(DBMessage)
        .filter(DBMessage.session_id == session_id, DBMessage.is_summarized == False)
        .order_by(DBMessage.created_at.asc())
        .all()
    )
    
    past_unsummarized = unsummarized_msgs[:-1] if unsummarized_msgs else []
    
    history_text = ""
    if session.summary:
        history_text += f"TÓM TẮT LỊCH SỬ CHAT CŨ:\n{session.summary}\n\n"
    
    history_text += build_history_text(past_unsummarized)

    # Lên lịch chạy ngầm task tóm tắt sau khi luồng này trả về kết quả cho user
    background_tasks.add_task(summarize_memory_task, session_id)

    async def wrapped_stream():
        ai_payload = {
            "session_id": session_id,
            "question": actual_question,
            "history_text": history_text
        }
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", f"{AI_AGENT_URL}/internal/chat", json=ai_payload) as response:
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
                                        sources=data.get("sources", []),
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
@limiter.limit("10/minute")
async def summarize_section_endpoint(
    request: Request,
    session_id: str,
    payload: SummarizeSectionRequest,
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

    actual_question = f"Hãy tóm tắt chi tiết toàn bộ nội dung của phần/chương có tên là: '{payload.section_title}'."

    async def wrapped_stream():
        ai_payload = {
            "session_id": session_id,
            "question": actual_question,
            "history_text": "",
            "section_title": payload.section_title,
            "level": payload.level
        }
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", f"{AI_AGENT_URL}/internal/chat", json=ai_payload) as response:
                async for chunk in response.aiter_lines():
                    if chunk:
                        sse_string = chunk + "\n\n"
                        if '"_save_answer"' in sse_string:
                            continue
                        yield sse_string

    return StreamingResponse(wrapped_stream(), media_type="text/event-stream")
