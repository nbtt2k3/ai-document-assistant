"""
rag/chain.py — LangChain RAG pipeline.

Xây dựng Hybrid Retriever (BM25 + Vector) + LLM chain cho từng session.
Đây là trung tâm của RAG engine.
"""
import os
import contextvars
from operator import itemgetter
from typing import List

from langchain.retrievers import EnsembleRetriever
from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

from src.app.rag.config import LLM_MODEL
from src.app.rag.vectorstore import get_retriever_for_session
from src.app.rag.bm25 import get_bm25_results

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


# ── Prompt template ───────────────────────────────────────────────────────────

_RAG_PROMPT_TEMPLATE = """Bạn là trợ lý AI thông minh đa ngôn ngữ.

TÀI LIỆU THAM KHẢO:
{context}

{chat_history}Câu hỏi hiện tại: {question}

HƯỚNG DẪN TRẢ LỜI:
- BẮT BUỘC trả lời bằng ngôn ngữ khớp với Câu hỏi.
- Nếu câu hỏi đề cập đến cuộc trò chuyện trước, hãy dùng LỊCH SỬ HỘI THOẠI để hiểu ngữ cảnh.
- Chỉ sử dụng thông tin từ tài liệu được cung cấp. 
- Trình bày rõ ràng, dễ đọc.
- Nếu trong tài liệu KHÔNG CÓ thông tin phù hợp để trả lời, bạn BẮT BUỘC phải trả lời bằng ĐÚNG một câu này: "Tôi chưa có thông tin về vấn đề này." và KHÔNG ĐƯỢC sinh thêm câu hỏi gợi ý ([SUGGESTIONS]).

QUAN TRỌNG: CHỈ KHI BẠN TÌM THẤY THÔNG TIN ĐỂ TRẢ LỜI, ở dòng cuối cùng của câu trả lời, bạn phải tạo ra 3 câu hỏi tiếp theo (Follow-up questions) liên quan đến nội dung vừa trả lời.
Tuyệt đối tuân thủ định dạng sau ở cuối cùng (các câu hỏi cách nhau bởi dấu gạch dọc "|"):
[SUGGESTIONS] <câu hỏi 1> | <câu hỏi 2> | <câu hỏi 3>

Ví dụ hợp lệ:
[SUGGESTIONS] Thẻ tín dụng là gì? | Cách bảo mật thẻ? | Phí thường niên bao nhiêu?

Trả lời:"""

_STOP_SEQUENCES = [
    "\nCâu hỏi:", "\n\nCâu hỏi:", "\nCÂU HỎI:", "\n\nCÂU HỎI:",
    "\nA:", "\n\nA:", "\nQ:", "\n\nQ:", "\nNote:", "\n\nNote:",
    "\nLưu ý:", "\n\nLưu ý:", "\nHuman:", "\n\nHuman:", "\n🧑", "\nBạn:",
]


# ── BM25 Retriever wrapper ─────────────────────────────────────────────────────

class SessionBM25Retriever(BaseRetriever):
    """LangChain-compatible retriever wrapper cho BM25 per-session."""
    session_id: str

    def _get_relevant_documents(self, query: str, *, run_manager=None) -> List[Document]:
        return get_bm25_results(self.session_id, query, k=8)


# ── RAG Chain factory ─────────────────────────────────────────────────────────

def create_rag_chain_for_session(session_id: str):
    """Tạo Hybrid RAG chain (BM25 + Vector + LLM) riêng cho một session."""

    # 1. Vector retriever (Chroma, filter theo session_id)
    vector_retriever = get_retriever_for_session(session_id)

    # 2. BM25 retriever (RAM-based, per-session)
    bm25_retriever = SessionBM25Retriever(session_id=session_id)

    # 3. Hybrid: 50% BM25 + 50% Vector
    retriever = EnsembleRetriever(
        retrievers=[bm25_retriever, vector_retriever],
        weights=[0.5, 0.5]
    )

    llm = OllamaLLM(
        model=LLM_MODEL,
        temperature=0.0,
        stop=_STOP_SEQUENCES,
    )

    prompt = ChatPromptTemplate.from_template(_RAG_PROMPT_TEMPLATE)

    chain = (
        {
            "context":      itemgetter("question") | retriever | format_docs,
            "question":     itemgetter("question"),
            "chat_history": itemgetter("chat_history"),
        }
        | prompt
        | llm
        | StrOutputParser()
    )

    return chain
