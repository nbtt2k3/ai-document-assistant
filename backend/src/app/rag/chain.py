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

from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

from src.app.rag.config import (
    LLM_MODEL, 
    OPENAI_API_KEY, OPENAI_LLM_MODEL,
    GEMINI_API_KEY, GEMINI_LLM_MODEL
)
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

_RAG_PROMPT_TEMPLATE = """Bạn là một trợ lý AI thông minh, thân thiện và hữu ích (có phong cách trò chuyện tự nhiên, nhiệt tình giống như một chuyên gia). 

TÀI LIỆU CUNG CẤP (Ngữ cảnh):
{context}

LỊCH SỬ CHAT:
{chat_history}

CÂU HỎI CỦA NGƯỜI DÙNG: {question}

QUY TẮC PHẢN HỒI:
1. TRƯỜNG HỢP NGƯỜI DÙNG VỪA TẢI FILE LÊN (Câu hỏi chứa cụm "[SYSTEM] File"): 
   - Hãy mở đầu bằng câu chào thân thiện thông báo đã nhận file, sau đó tự động tóm tắt ngắn gọn và mạch lạc nội dung chính của TÀI LIỆU CUNG CẤP để người dùng nắm được tổng quan.
2. TRƯỜNG HỢP CÂU HỎI BÌNH THƯỜNG:
   - Luôn trả lời một cách tự nhiên, lịch sự, rõ ràng và chi tiết dựa trên TÀI LIỆU CUNG CẤP.
   - Nếu câu hỏi không liên quan đến tài liệu hoặc không tìm thấy thông tin trong tài liệu, hãy thành thật trả lời lịch sự. Tuyệt đối KHÔNG tự bịa đặt thông tin.
3. NGÔN NGỮ (QUAN TRỌNG NHẤT): 
   - Ngôn ngữ phản hồi BẮT BUỘC phải theo ngôn ngữ hội thoại hiện tại của người dùng, KHÔNG phụ thuộc vào ngôn ngữ của tài liệu.
   - Mặc định: Nếu đây là tin nhắn đầu tiên (chưa có lịch sử chat), LUÔN LUÔN phản hồi bằng Tiếng Việt.
   - Ví dụ: Nếu người dùng đang chat bằng tiếng Việt, bạn phải tóm tắt file và trả lời câu hỏi bằng tiếng Việt, dù tài liệu tải lên là tiếng Anh hay tiếng Nhật. Nếu người dùng đổi sang chat tiếng Anh, bạn mới đổi sang trả lời tiếng Anh.
   - KHÔNG dùng Tiếng Trung.
4. GỢI Ý: BẮT BUỘC chèn 3 câu hỏi gợi ý liên quan đến tài liệu ở cuối cùng theo ĐÚNG định dạng thẻ [SUGGESTIONS] bên dưới. Đảm bảo ngôn ngữ của câu hỏi gợi ý CÙNG NGÔN NGỮ với câu trả lời của bạn.

ĐỊNH DẠNG ĐẦU RA BẮT BUỘC:
(Nội dung câu trả lời tự nhiên của bạn...)

[SUGGESTIONS] Câu hỏi gợi ý 1? | Câu hỏi gợi ý 2? | Câu hỏi gợi ý 3?

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
        return get_bm25_results(self.session_id, query, k=3)


# ── RAG Chain factory ─────────────────────────────────────────────────────────

def create_rag_chain_for_session(session_id: str, section_title: str = None, level: int = None):
    """Tạo Hybrid RAG chain (BM25 + Vector + LLM) riêng cho một session."""

    if section_title and level:
        from src.app.rag.vectorstore import get_retriever_for_section
        # Chỉ dùng vector retriever để lấy toàn bộ chunk của mục này
        retriever = get_retriever_for_section(session_id, section_title, level)
    else:
        # 1. Vector retriever (Chroma, filter theo session_id)
        vector_retriever = get_retriever_for_session(session_id)

        # 2. BM25 retriever (RAM-based, per-session)
        bm25_retriever = SessionBM25Retriever(session_id=session_id)

        # 3. Hybrid: 50% BM25 + 50% Vector
        retriever = EnsembleRetriever(
            retrievers=[bm25_retriever, vector_retriever],
            weights=[0.5, 0.5]
        )

    # Chọn LLM dựa trên cấu hình API key
    if OPENAI_API_KEY:
        print(f"[INFO] Dang su dung LLM Online: OpenAI ({OPENAI_LLM_MODEL})")
        llm = ChatOpenAI(
            model=OPENAI_LLM_MODEL,
            api_key=OPENAI_API_KEY,
            temperature=0.0,
            stop=_STOP_SEQUENCES,
        )
    elif GEMINI_API_KEY:
        print(f"[INFO] Dang su dung LLM Online: Gemini ({GEMINI_LLM_MODEL})")
        llm = ChatGoogleGenerativeAI(
            model=GEMINI_LLM_MODEL,
            google_api_key=GEMINI_API_KEY,
            temperature=0.0,
            stop=_STOP_SEQUENCES,
        )
    else:
        print(f"[INFO] Dang su dung LLM Local: Ollama ({LLM_MODEL})")
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
