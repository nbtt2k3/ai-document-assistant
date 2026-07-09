"""
rag/vectorstore.py — ChromaDB vector store wrapper.

Quản lý việc lưu trữ, tìm kiếm và xóa vectors theo session_id.
Embedding được lấy từ embedder.py (dễ swap provider).

Tích hợp ParentDocumentRetriever và MarkdownHeaderTextSplitter để
giữ nguyên cấu trúc văn bản và tránh mất ngữ cảnh.
"""
from langchain_classic.retrievers import ParentDocumentRetriever
from langchain_text_splitters import RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter
from langchain_core.stores import BaseStore
from langchain_chroma import Chroma
from langchain_core.documents import Document
import os
import json
from typing import Sequence, Optional, Iterator
import logging

from src.app.config import VECTORSTORE_PATH, DOCSTORE_PATH, CHUNK_SIZE, CHUNK_OVERLAP
from src.app.rag.embedder import get_embedder


# ── Singletons ──────────────────────────────────────────────────────────────
_chroma_db: Chroma = None
_docstore = None


class LocalFileDocStore(BaseStore[str, Document]):
    def __init__(self, path: str):
        self.path = path
        os.makedirs(path, exist_ok=True)
        
    def _get_path(self, key: str) -> str:
        return os.path.join(self.path, f"{key}.json")
        
    def mget(self, keys: Sequence[str]) -> list[Optional[Document]]:
        docs = []
        for key in keys:
            p = self._get_path(key)
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    docs.append(Document(page_content=data["page_content"], metadata=data["metadata"]))
            else:
                docs.append(None)
        return docs
        
    def mset(self, key_value_pairs: Sequence[tuple[str, Document]]) -> None:
        for key, doc in key_value_pairs:
            p = self._get_path(key)
            with open(p, "w", encoding="utf-8") as f:
                json.dump({"page_content": doc.page_content, "metadata": doc.metadata}, f, ensure_ascii=False)
                
    def mdelete(self, keys: Sequence[str]) -> None:
        for key in keys:
            p = self._get_path(key)
            if os.path.exists(p):
                os.remove(p)
                
    def yield_keys(self, prefix: Optional[str] = None) -> Iterator[str]:
        for file in os.listdir(self.path):
            if file.endswith(".json"):
                key = file[:-5]
                if prefix is None or key.startswith(prefix):
                    yield key


def _get_chroma_db() -> Chroma:
    """Trả về Chroma singleton instance."""
    global _chroma_db
    if _chroma_db is not None:
        return _chroma_db
    _chroma_db = Chroma(
        persist_directory=VECTORSTORE_PATH,
        embedding_function=get_embedder()
    )
    return _chroma_db


def _get_docstore():
    """Trả về DocStore singleton instance cho ParentDocuments."""
    global _docstore
    if _docstore is not None:
        return _docstore
        
    _docstore = LocalFileDocStore(DOCSTORE_PATH)
    return _docstore


def _get_child_splitter() -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        separators=["\n\n", "\n", ".", " ", ""]
    )


def add_documents_to_session(session_id: str, docs: list[Document]):
    """Thêm documents vào hệ thống với Parent-Child Retriever."""
    db = _get_chroma_db()
    store = _get_docstore()
    
    # 1. Tách văn bản theo cấu trúc Markdown Header (Parent Docs)
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ]
    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    
    parent_docs = []
    for doc in docs:
        splits = markdown_splitter.split_text(doc.page_content)
        if not splits: # Nếu không có header nào, lấy nguyên văn bản
            doc.metadata["session_id"] = session_id
            parent_docs.append(doc)
            continue
            
        for split in splits:
            # Gộp metadata gốc và thêm session_id
            split.metadata.update(doc.metadata)
            split.metadata["session_id"] = session_id
            parent_docs.append(split)

    # 2. Đưa vào ParentDocumentRetriever để tự động tạo Child Chunks
    retriever = ParentDocumentRetriever(
        vectorstore=db,
        docstore=store,
        child_splitter=_get_child_splitter()
    )
    
    # Thêm vào hệ thống (Chroma lưu Child, DocStore lưu Parent)
    retriever.add_documents(parent_docs)


def get_retriever_for_session(session_id: str):
    """Lấy ParentDocumentRetriever với filter theo session_id."""
    db = _get_chroma_db()
    store = _get_docstore()

    # Đếm số lượng child chunks thực tế để tránh lỗi hnswlib
    try:
        results = db.get(where={"session_id": session_id}, include=[])
        num_chunks = len(results.get("ids", []))
    except Exception:
        num_chunks = 3

    k = min(5, num_chunks) if num_chunks > 0 else 1

    return ParentDocumentRetriever(
        vectorstore=db,
        docstore=store,
        child_splitter=_get_child_splitter(),
        search_kwargs={
            "k": k,
            "filter": {"session_id": session_id}
        }
    )


def get_retriever_for_section(session_id: str, section_title: str, level: int):
    """Lấy Retriever chỉ filter các chunk thuộc một section cụ thể."""
    db = _get_chroma_db()
    store = _get_docstore()
    header_key = f"Header {level}"
    
    return ParentDocumentRetriever(
        vectorstore=db,
        docstore=store,
        child_splitter=_get_child_splitter(),
        search_kwargs={
            "k": 100,  # Lấy nhiều nhất có thể cho một section
            "filter": {
                "$and": [
                    {"session_id": session_id},
                    {header_key: section_title}
                ]
            }
        }
    )


def get_session_metadatas(session_id: str) -> list[dict]:
    """Lấy tất cả metadatas của một session từ Chroma (Child chunks)."""
    db = _get_chroma_db()
    try:
        results = db.get(where={"session_id": session_id}, include=["metadatas"])
        return results.get("metadatas", [])
    except Exception:
        return []


def get_session_documents(session_id: str) -> list[Document]:
    """
    Lấy tất cả child documents của một session từ Chroma.
    """
    db = _get_chroma_db()
    try:
        results = db.get(
            where={"session_id": session_id},
            include=["documents", "metadatas"]
        )
        docs = []
        texts = results.get("documents", [])
        metas = results.get("metadatas", [])
        for text, meta in zip(texts, metas):
            if text:
                docs.append(Document(page_content=text, metadata=meta or {}))
        return docs
    except Exception as e:
        logging.error(f"[vectorstore] Error fetching documents for session {session_id}: {e}")
        return []

def get_all_parent_documents(session_id: str) -> list[Document]:
    """Lấy tất cả Parent Documents của một session để dùng cho Map-Reduce."""
    db = _get_chroma_db()
    store = _get_docstore()
    try:
        # Lấy metadatas để tìm doc_id của Parent Documents
        results = db.get(where={"session_id": session_id}, include=["metadatas"])
        metadatas = results.get("metadatas", [])
        
        doc_ids = set()
        for meta in metadatas:
            if meta and "doc_id" in meta:
                doc_ids.add(meta["doc_id"])
                
        if not doc_ids:
            return []
            
        parent_docs = store.mget(list(doc_ids))
        # Filter out Nones
        return [doc for doc in parent_docs if doc]
    except Exception as e:
        logging.error(f"[vectorstore] Error fetching parent documents for session {session_id}: {e}")
        return []


def remove_documents_for_session(session_id: str):
    """Xóa tất cả vectors và parent documents của một session."""
    db = _get_chroma_db()
    store = _get_docstore()
    try:
        # Lấy metadatas để tìm doc_id của Parent Documents
        results = db.get(where={"session_id": session_id}, include=["metadatas"])
        metadatas = results.get("metadatas", [])
        
        doc_ids = set()
        for meta in metadatas:
            if meta and "doc_id" in meta:
                doc_ids.add(meta["doc_id"])
                
        # Xóa Parent Documents khỏi LocalFileStore
        if doc_ids:
            store.mdelete(list(doc_ids))
            
        # Xóa Child Chunks khỏi Chroma
        db.delete(where={"session_id": session_id})
    except Exception as e:
        logging.error(f"[vectorstore] Error removing session {session_id}: {e}")
