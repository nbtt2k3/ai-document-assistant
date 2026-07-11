"""
rag/bm25.py — BM25 keyword search engine.

Lưu trữ BM25 index trên RAM (per-session) để tìm kiếm từ khoá nhanh.
Kết hợp với vectorstore.py trong hybrid retriever.

Auto-rebuild: nếu index không có trong RAM (vd: sau khi container restart),
tự động rebuild từ ChromaDB để không mất tính năng keyword search.

Vietnamese tokenization: sử dụng underthesea nếu có, fallback về whitespace split.
"""
from rank_bm25 import BM25Okapi
from langchain_core.documents import Document
from typing import Dict, List
import string
import logging

# ── Vietnamese tokenizer (optional) ──────────────────────────────────────────
# underthesea tách từ tiếng Việt chính xác hơn whitespace split
# Cài: pip install underthesea
try:
    from underthesea import word_tokenize as _vi_tokenize
    _HAS_UNDERTHESEA = True
    logging.info("[bm25] Sử dụng underthesea cho Vietnamese tokenization")
except ImportError:
    _HAS_UNDERTHESEA = False
    logging.info("[bm25] underthesea không có, dùng whitespace tokenization (pip install underthesea để cải thiện)")


# Dictionary lưu trữ BM25 index trên RAM, key là session_id
_bm25_indices: Dict[str, BM25Okapi] = {}
_bm25_docs: Dict[str, List[Document]] = {}


def _preprocess(text: str) -> list[str]:
    """Tiền xử lý text cho BM25: chuyển thường, bỏ dấu câu, tách từ.

    Dùng underthesea.word_tokenize nếu có (tốt hơn cho tiếng Việt),
    fallback về whitespace split nếu chưa cài underthesea.
    """
    text = text.lower()
    text = text.translate(str.maketrans('', '', string.punctuation))
    if _HAS_UNDERTHESEA:
        try:
            return _vi_tokenize(text, format="text").split()
        except Exception:
            pass  # Fallback nếu underthesea lỗi (vd: text quá ngắn)
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


def _try_rebuild_from_chroma(session_id: str) -> bool:
    """
    Thử rebuild BM25 index từ ChromaDB khi không có trong RAM.
    Xảy ra khi container restart và RAM index bị mất.

    Returns:
        True nếu rebuild thành công, False nếu không có dữ liệu.
    """
    try:
        from src.app.rag.vectorstore import get_session_documents
        docs = get_session_documents(session_id)
        if docs:
            build_bm25_for_session(session_id, docs)
            print(f"[bm25] Auto-rebuilt index cho session '{session_id}' từ ChromaDB ({len(docs)} chunks)")
            return True
    except Exception as e:
        print(f"[bm25] Không thể rebuild index từ ChromaDB: {e}")
    return False


def get_bm25_results(session_id: str, query: str, k: int = 8, target_filename: str = None) -> List[Document]:
    """
    Tìm kiếm bằng BM25 cho một session cụ thể.
    Tự động rebuild từ ChromaDB nếu index không có trong RAM.
    """
    # Auto-rebuild nếu index bị mất (vd: sau khi container restart)
    if session_id not in _bm25_indices or session_id not in _bm25_docs:
        if not _try_rebuild_from_chroma(session_id):
            return []

    docs = _bm25_docs[session_id]
    
    if target_filename:
        docs = [d for d in docs if target_filename.lower() in d.metadata.get("source", "").lower()]
        if not docs:
            return []
        tokenized_corpus = [_preprocess(doc.page_content) for doc in docs]
        bm25 = BM25Okapi(tokenized_corpus)
    else:
        bm25 = _bm25_indices[session_id]

    tokenized_query = _preprocess(query)
    return bm25.get_top_n(tokenized_query, docs, n=k)


def remove_bm25_for_session(session_id: str):
    """Giải phóng RAM khi session bị xoá hoặc không còn active."""
    if session_id in _bm25_indices:
        del _bm25_indices[session_id]
    if session_id in _bm25_docs:
        del _bm25_docs[session_id]
