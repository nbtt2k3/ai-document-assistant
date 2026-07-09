"""
services/chat_service.py — Orchestration cho việc xử lý hỏi-đáp.

Điều phối pipeline RAG:
  Câu hỏi + Lịch sử → RAG chain → Stream kết quả (SSE)
  Sau khi có full_answer → sinh câu hỏi gợi ý bám sát nội dung → SSE event "suggestions"

API layer chỉ cần gọi build_history_text() và create_event_stream(),
không cần biết LangChain hay LLM hoạt động như thế nào.
"""
import json
import logging
from typing import AsyncGenerator

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from src.app.rag.chain import create_rag_chain_for_session
from src.app.rag.llm_factory import get_llm
from src.app.prompts.prompt_manager import PromptManager
from src.app.rag.utils import get_last_sources, clean_output, reset_sources

# Độ dài tối đa của answer trước khi truyền vào prompt gợi ý
_SUGGESTIONS_ANSWER_MAX_CHARS = 3000


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


async def generate_suggestions(answer: str, context: str) -> list[str]:
    """
    Sinh câu hỏi gợi ý bám sát nội dung câu trả lời vừa cung cấp, 
    nhưng CHỈ ĐƯỢC PHÉP gợi ý những thứ mà context có thông tin để trả lời.

    Args:
        answer: Nội dung câu trả lời đầy đủ từ LLM.
        context: Nội dung tài liệu liên quan đã retrieve.

    Returns:
        Danh sách 0–3 câu hỏi gợi ý. Trả về [] nếu không có gợi ý phù hợp.
    """
    try:
        # Truncate answer & context để tránh vượt context limit
        answer_for_prompt = answer[:_SUGGESTIONS_ANSWER_MAX_CHARS] if len(answer) > _SUGGESTIONS_ANSWER_MAX_CHARS else answer
        context_for_prompt = context[:_SUGGESTIONS_ANSWER_MAX_CHARS * 2] if len(context) > _SUGGESTIONS_ANSWER_MAX_CHARS * 2 else context

        llm = get_llm()
        prompt = ChatPromptTemplate.from_messages(PromptManager.get_langchain_messages("suggestions"))
        chain = prompt | llm | StrOutputParser()
        raw = await chain.ainvoke({
            "answer": answer_for_prompt,
            "context": context_for_prompt
        })

        # Tìm JSON array trong output (phòng trường hợp LLM trả về text thừa)
        raw = raw.strip()
        start = raw.find("[")
        end = raw.rfind("]")
        if start == -1 or end == -1 or end < start:
            return []

        parsed = json.loads(raw[start:end + 1])
        if not isinstance(parsed, list):
            return []

        # Lọc chỉ giữ chuỗi hợp lệ, tối đa 3 câu
        suggestions = [s.strip() for s in parsed if isinstance(s, str) and len(s.strip()) > 5]
        return suggestions[:3]

    except Exception as e:
        logging.warning(f"[chat_service] generate_suggestions error: {e}")
        return []


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
        Chuỗi SSE events: chunk, final_answer, suggestions, sources, [DONE], error.

    Args:
        session_id   : Session cần query.
        question     : Câu hỏi thực sự của user (đã bỏ [SYSTEM] prefix).
        history_text : Lịch sử hội thoại đã định dạng (từ build_history_text).
        section_title: (Optional) Tên chương mục cần tóm tắt.
        level        : (Optional) Cấp độ của chương mục (1, 2, 3).
    """
    # Reset sources trước mỗi request — tránh rò rỉ từ request trước nếu intent là CHITCHAT
    reset_sources()
    graph = create_rag_chain_for_session(session_id, section_title, level)
    raw_chunks = []

    # Thay vì dùng ContextVar dễ bị mất giữa các luồng async, ta trích xuất trực tiếp từ graph events
    retrieved_docs = []

    try:
        inputs = {"question": question, "chat_history": history_text}

        # Định nghĩa các thông báo suy nghĩ cho từng Node
        NODE_THOUGHTS = {
            "route_question": "🧠 Đang phân tích ý định câu hỏi...",
            "retrieve": "🔍 Đang lục tìm tài liệu liên quan...",
            "retrieve_for_summarize": "🔍 Đang lục tìm tài liệu liên quan...",
            "retrieve_for_translate": "🔍 Đang lục tìm tài liệu liên quan...",
            "grade_documents": "⚖️ Đang đánh giá độ chính xác của tài liệu tìm được...",
            "rewrite_query": "🔄 Tài liệu chưa đủ tốt, đang viết lại câu hỏi tìm kiếm sâu hơn...",
            "generate_rag": "📝 Đang tổng hợp câu trả lời cuối cùng...",
            "summarize": "📝 Đang tiến hành tóm tắt văn bản...",
            "translate": "📝 Đang dịch thuật văn bản...",
            "chitchat": "💬 Đang tạo phản hồi..."
        }

        async for event in graph.astream_events(inputs, version="v2"):
            # Bắt sự kiện bắt đầu một Node để stream 'thought'
            if event["event"] == "on_chain_start":
                node_name = event.get("name")
                if node_name in NODE_THOUGHTS:
                    thought_msg = NODE_THOUGHTS[node_name]
                    data_thought = json.dumps({"type": "thought", "content": thought_msg}, ensure_ascii=False)
                    yield f"data: {data_thought}\n\n"

            # Bắt output của node retrieve để lấy documents
            if event["event"] == "on_chain_end" and event.get("name") in ["retrieve", "retrieve_for_summarize", "retrieve_for_translate", "summarize"]:
                output = event.get("data", {}).get("output", {})
                if isinstance(output, dict) and "documents" in output:
                    retrieved_docs = output["documents"]

            if event["event"] == "on_chat_model_stream" and "final_generation" in event.get("tags", []):
                chunk_content = event["data"]["chunk"].content
                if chunk_content:
                    raw_chunks.append(chunk_content)
                    data = json.dumps({"type": "chunk", "content": chunk_content}, ensure_ascii=False)
                    yield f"data: {data}\n\n"

        full_answer = clean_output("".join(raw_chunks))

        # Gửi câu trả lời hoàn chỉnh
        data_final = json.dumps(
            {"type": "final_answer", "content": full_answer}, ensure_ascii=False
        )
        yield f"data: {data_final}\n\n"

        import os
        # Build sources array từ retrieved_docs
        sources = [
            {
                "file": os.path.basename(doc.metadata.get("source", "unknown")),
                "page": doc.metadata.get("page", "?"),
                "text": doc.page_content,
            }
            for doc in retrieved_docs
        ]
        
        # Build context string từ sources để phục vụ suggestions
        context_str = "\n\n".join([s.get("text", "") for s in sources])
        
        # Đã tắt tính năng gợi ý câu hỏi theo yêu cầu
        # suggestions = await generate_suggestions(full_answer, context_str)
        data_suggestions = json.dumps(
            {"type": "suggestions", "content": []}, ensure_ascii=False
        )
        yield f"data: {data_suggestions}\n\n"

        # Lọc unique sources
        unique_sources = _unique_sources(sources)
        
        # Trả về full_answer và sources (CÓ CHỨA TEXT) để API layer lưu vào DB
        data_save = json.dumps(
            {"type": "_save_answer", "content": full_answer, "sources": unique_sources}, ensure_ascii=False
        )
        yield f"data: {data_save}\n\n"

        # TẠO BẢN SAO để KHÔNG GỬI 'text' qua giao diện Web nhằm tiết kiệm băng thông mạng
        frontend_sources = []
        for s in unique_sources:
            s_copy = s.copy()
            if "text" in s_copy:
                del s_copy["text"]
            frontend_sources.append(s_copy)

        data_sources = json.dumps(
            {"type": "sources", "content": frontend_sources}, ensure_ascii=False
        )
        yield f"data: {data_sources}\n\n"

    except Exception as e:
        logging.error(f"[chat_service] Streaming error: {e}")
        error_data = json.dumps({"type": "error", "content": str(e)}, ensure_ascii=False)
        yield f"data: {error_data}\n\n"
    finally:
        yield "data: [DONE]\n\n"


async def summarize_memory(old_summary: str, new_messages: str) -> str:
    """
    Tóm tắt lịch sử hội thoại cũ và mới thành một bản tóm tắt duy nhất.
    Async để không block event loop của FastAPI.
    """
    prompt = ChatPromptTemplate.from_messages(PromptManager.get_langchain_messages("memory_summary"))
    chain = prompt | get_llm() | StrOutputParser()

    return await chain.ainvoke({
        "old_summary": old_summary or "Không có tóm tắt cũ.",
        "new_messages": new_messages or "Không có tin nhắn mới."
    })
