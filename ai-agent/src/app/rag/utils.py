"""
rag/utils.py — Utility functions cho RAG pipeline.

Chứa:
- format_docs: định dạng Documents thành context string cho LLM
- clean_output: cắt bỏ hallucination
- Citation tracking: theo dõi nguồn tài liệu thread-safe
"""
import os
import contextvars

from langchain_core.documents import Document


# ── Thread-safe citation tracking ─────────────────────────────────────────────
_last_retrieved_sources: contextvars.ContextVar[list[dict]] = contextvars.ContextVar(
    "_last_retrieved_sources", default=[]
)


def get_last_sources() -> list[dict]:
    """Trả về danh sách nguồn tài liệu của lần retrieve gần nhất."""
    return _last_retrieved_sources.get()


def format_docs(docs: list[Document]) -> str:
    """Định dạng Documents thành context string cho LLM, đồng thời ghi lại citations."""
    sources = [
        {
            "file": os.path.basename(doc.metadata.get("source", "unknown")),
            "page": doc.metadata.get("page", "?"),
        }
        for doc in docs
    ]
    _last_retrieved_sources.set(sources)

    return "\n\n".join(
        f"[Trang {doc.metadata.get('page', '?')} - {os.path.basename(doc.metadata.get('source', 'unknown'))}]\n"
        f"{doc.page_content}"
        for doc in docs
    )


def clean_output(text: str) -> str:
    """Cắt bỏ phần hallucination phía sau câu trả lời (Q:, Note:, Human:, ...)."""
    cutoff_markers = [
        "\nA:", "\n\nA:", "\nNote:", "\n\nNote:", "\nLưu ý:", "\n\nLưu ý:",
        "\nCâu hỏi:", "\n\nCâu hỏi:", "\nQ:", "\n\nQ:", "\nHuman:", "\n\nHuman:",
        "\n(Đây là", "\n\n(Đây là", "\nĐây là",
        "\n🔹 Yêu cầu:", "\n🔹 Yêu Cầu:", "\nYêu cầu:", "\nYÊU CẦU:",
        "\n🔹 Quy tắc định dạng:", "\nQuy tắc định dạng:",
    ]
    result = text.strip()
    for marker in cutoff_markers:
        if marker in result:
            result = result[:result.index(marker)].strip()
    return result
