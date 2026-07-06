"""
rag/bm25.py — BM25 keyword search engine.

Lưu trữ BM25 index trên RAM (per-session) để tìm kiếm từ khoá nhanh.
Kết hợp với vectorstore.py trong hybrid retriever.
"""
from rank_bm25 import BM25Okapi
from langchain_core.documents import Document
from typing import Dict, List
import string

# Dictionary lưu trữ BM25 index trên RAM, key là session_id
_bm25_indices: Dict[str, BM25Okapi] = {}
_bm25_docs: Dict[str, List[Document]] = {}


def _preprocess(text: str) -> list[str]:
    """Tiền xử lý text cho BM25 (chuyển thường, bỏ dấu câu, tách từ)."""
    text = text.lower()
    text = text.translate(str.maketrans('', '', string.punctuation))
    return text.split()


def build_bm25_for_session(session_id: str, docs: List[Document]):
    """Thêm documents vào BM25 index cho một session và lưu vào RAM."""
    if not docs:
        return

    existing_docs = _bm25_docs.get(session_id, [])
    all_docs = existing_docs + docs

    tokenized_corpus = [_preprocess(doc.page_content) for doc in all_docs]
    bm25 = BM25Okapi(tokenized_corpus)

    _bm25_indices[session_id] = bm25
    _bm25_docs[session_id] = all_docs


def get_bm25_results(session_id: str, query: str, k: int = 8) -> List[Document]:
    """Tìm kiếm bằng BM25 cho một session cụ thể."""
    if session_id not in _bm25_indices or session_id not in _bm25_docs:
        return []

    bm25 = _bm25_indices[session_id]
    docs = _bm25_docs[session_id]

    tokenized_query = _preprocess(query)
    return bm25.get_top_n(tokenized_query, docs, n=k)


def remove_bm25_for_session(session_id: str):
    """Giải phóng RAM khi session bị xoá hoặc không còn active."""
    if session_id in _bm25_indices:
        del _bm25_indices[session_id]
    if session_id in _bm25_docs:
        del _bm25_docs[session_id]
