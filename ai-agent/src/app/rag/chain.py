"""
rag/chain.py — LangChain RAG pipeline assembly.

Xây dựng Hybrid Retriever (BM25 + Vector) + LLM chain cho từng session.
Đây là trung tâm của RAG engine.

Các thành phần được import từ:
- prompts/prompt_manager.py: Prompt templates
- llm_factory.py  : LLM provider selection (singleton)
- utils.py        : format_docs, clean_output, citations
"""
from typing import List

from langchain_classic.retrievers import EnsembleRetriever, ContextualCompressionRetriever
from langchain_classic.retrievers.multi_query import MultiQueryRetriever
from langchain_community.document_compressors.flashrank_rerank import FlashrankRerank
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

from src.app.rag.llm_factory import get_llm

from src.app.rag.vectorstore import get_retriever_for_session
from src.app.rag.bm25 import get_bm25_results
from src.app.config import RERANK_TOP_N


# ── BM25 Retriever wrapper ─────────────────────────────────────────────────────

class SessionBM25Retriever(BaseRetriever):
    """LangChain-compatible retriever wrapper cho BM25 per-session."""
    session_id: str

    def _get_relevant_documents(self, query: str, *, run_manager=None) -> List[Document]:
        return get_bm25_results(self.session_id, query, k=3)


def get_base_retriever(session_id: str, section_title: str = None, level: int = None):
    """
    Tạo Hybrid Retriever (BM25 + Vector + Rerank).
    MultiQueryRetriever chỉ bật khi dùng API online để tiết kiệm VRAM với Ollama local.
    """
    if section_title and level:
        from src.app.rag.vectorstore import get_retriever_for_section
        return get_retriever_for_section(session_id, section_title, level)

    from src.app.rag.vectorstore import get_retriever_for_session
    vector_retriever = get_retriever_for_session(session_id)
    bm25_retriever = SessionBM25Retriever(session_id=session_id)

    base_retriever = EnsembleRetriever(
        retrievers=[bm25_retriever, vector_retriever],
        weights=[0.5, 0.5]
    )

    llm = get_llm()

    # MultiQueryRetriever sinh nhiều biến thể câu hỏi để tăng recall
    # Singleton LLM đảm bảo không tạo thêm CUDA context dù gọi nhiều lần
    intermediate_retriever = MultiQueryRetriever.from_llm(
        retriever=base_retriever, llm=llm
    )

    # Khởi tạo trực tiếp Ranker để ép dùng cache_dir vĩnh viễn, tránh flashrank tự xoá /tmp và tải lại
    from flashrank import Ranker
    from langchain_community.document_compressors.flashrank_rerank import DEFAULT_MODEL_NAME
    
    ranker_client = Ranker(model_name=DEFAULT_MODEL_NAME, cache_dir="/app/flashrank_cache")
    compressor = FlashrankRerank(client=ranker_client, top_n=RERANK_TOP_N)
    
    retriever = ContextualCompressionRetriever(
        base_compressor=compressor, base_retriever=intermediate_retriever
    )
    return retriever


def create_rag_chain_for_session(session_id: str, section_title: str = None, level: int = None):
    """Tạo CRAG graph thay vì RunnableBranch cũ."""
    from src.app.rag.graph import create_crag_graph
    return create_crag_graph(session_id, section_title, level)
