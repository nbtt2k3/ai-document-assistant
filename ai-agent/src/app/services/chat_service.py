"""
services/chat_service.py — Orchestration cho việc xử lý hỏi-đáp.

Điều phối pipeline RAG:
  Câu hỏi + Lịch sử → RAG chain → Stream kết quả (SSE)

API layer chỉ cần gọi build_history_text() và create_event_stream(),
không cần biết LangChain hay LLM hoạt động như thế nào.
"""
import json
import logging
from typing import AsyncGenerator

from src.app.rag.chain import create_rag_chain_for_session
from src.app.rag.utils import get_last_sources, clean_output


def build_history_text(messages: list) -> str:
    """
    Định dạng lịch sử hội thoại thành chuỗi text cho LLM.

    Args:
        messages: List các Message ORM objects (có .role và .content).

    Returns:
        Chuỗi lịch sử đã định dạng, hoặc chuỗi rỗng nếu không có.
    """
    if not messages:
        return ""
    lines = ["LỊCH SỬ HỘI THOẠI GẦN ĐÂY (để hiểu ngữ cảnh):"]
    for msg in messages:
        role_label = "👤 Bạn" if msg.role == "user" else "🤖 Bot"
        lines.append(f"{role_label}: {msg.content}")
    lines.append("")
    return "\n".join(lines) + "\n"


def _unique_sources(sources: list[dict]) -> list[dict]:
    """Lọc bỏ các nguồn tài liệu trùng lặp (cùng file + page)."""
    seen = set()
    unique = []
    for s in sources:
        key = (s["file"], s["page"])
        if key not in seen:
            seen.add(key)
            unique.append(s)
    return unique


async def create_event_stream(
    session_id: str,
    question: str,
    history_text: str,
    section_title: str = None,
    level: int = None,
) -> AsyncGenerator[str, None]:
    """
    Generator cho SSE streaming — toàn bộ RAG pipeline.

    Yields:
        Chuỗi SSE events: chunk, final_answer, sources, [DONE], error.

    Args:
        session_id   : Session cần query.
        question     : Câu hỏi thực sự của user (đã bỏ [SYSTEM] prefix).
        history_text : Lịch sử hội thoại đã định dạng (từ build_history_text).
        section_title: (Optional) Tên chương mục cần tóm tắt.
        level        : (Optional) Cấp độ của chương mục (1, 2, 3).
    """
    chain = create_rag_chain_for_session(session_id, section_title, level)
    raw_chunks = []

    try:
        for chunk in chain.stream({"question": question, "chat_history": history_text}):
            raw_chunks.append(chunk)
            data = json.dumps({"type": "chunk", "content": chunk}, ensure_ascii=False)
            yield f"data: {data}\n\n"

        full_answer = clean_output("".join(raw_chunks))

        data_final = json.dumps(
            {"type": "final_answer", "content": full_answer}, ensure_ascii=False
        )
        yield f"data: {data_final}\n\n"

        sources = get_last_sources()
        data_sources = json.dumps(
            {"type": "sources", "content": _unique_sources(sources)}, ensure_ascii=False
        )
        yield f"data: {data_sources}\n\n"

        # Trả về full_answer để API layer lưu vào DB
        data_save = json.dumps(
            {"type": "_save_answer", "content": full_answer}, ensure_ascii=False
        )
        yield f"data: {data_save}\n\n"

    except Exception as e:
        logging.error(f"[chat_service] Streaming error: {e}")
        error_data = json.dumps({"type": "error", "content": str(e)}, ensure_ascii=False)
        yield f"data: {error_data}\n\n"
    finally:
        yield "data: [DONE]\n\n"


def summarize_memory(old_summary: str, new_messages: str) -> str:
    """Tóm tắt lịch sử hội thoại cũ và mới thành một bản tóm tắt duy nhất."""
    from src.app.rag.llm_factory import get_llm
    from src.app.rag.prompts import MEMORY_SUMMARY_PROMPT_TEMPLATE
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser

    prompt = ChatPromptTemplate.from_template(MEMORY_SUMMARY_PROMPT_TEMPLATE)
    chain = prompt | get_llm() | StrOutputParser()
    
    return chain.invoke({
        "old_summary": old_summary or "Không có tóm tắt cũ.",
        "new_messages": new_messages or "Không có tin nhắn mới."
    })
