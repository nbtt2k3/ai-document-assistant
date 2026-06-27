"""
rag/vectorstore.py — ChromaDB vector store wrapper.

Quản lý việc lưu trữ, tìm kiếm và xóa vectors theo session_id.
Embedding được lấy từ embedder.py (dễ swap provider).
"""
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_core.documents import Document

from src.app.core.config import VECTORSTORE_PATH
from src.app.rag.config import CHUNK_SIZE, CHUNK_OVERLAP
from src.app.rag.embedder import get_embedder


def _get_chroma_db() -> Chroma:
    """Khởi tạo Chroma DB instance với embedding function hiện tại."""
    return Chroma(
        persist_directory=VECTORSTORE_PATH,
        embedding_function=get_embedder()
    )


def _split_text(docs: list[Document]) -> list[Document]:
    """Chia nhỏ documents thành chunks để embedding."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        separators=["\n\n", "\n", ".", " ", ""]
    )
    return splitter.split_documents(docs)


def add_documents_to_session(session_id: str, docs: list[Document]):
    """Thêm documents vào Chroma, gắn tag session_id để filter sau."""
    for i, doc in enumerate(docs):
        doc.metadata["session_id"] = session_id
        doc.metadata["chunk_index"] = i

    splits = _split_text(docs)
    db = _get_chroma_db()
    db.add_documents(splits)


def get_retriever_for_session(session_id: str):
    """Lấy Chroma retriever với filter theo session_id."""
    db = _get_chroma_db()
    
    # Đếm số lượng chunks thực tế của session này để tránh lỗi hnswlib "Cannot return the results in a contigious 2D array"
    try:
        results = db.get(where={"session_id": session_id}, include=[])
        num_chunks = len(results.get("ids", []))
    except Exception:
        num_chunks = 3

    # Nếu không có chunk nào, vẫn set k=1 để Langchain không lỗi
    k = min(3, num_chunks) if num_chunks > 0 else 1

    return db.as_retriever(
        search_kwargs={
            "k": k,
            "filter": {"session_id": session_id}
        }
    )

def get_retriever_for_section(session_id: str, section_title: str, level: int):
    """Lấy Chroma retriever chỉ filter các chunk thuộc một section cụ thể."""
    db = _get_chroma_db()
    header_key = f"Header {level}"
    return db.as_retriever(
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


def remove_documents_for_session(session_id: str):
    """Xóa tất cả vectors của một session khỏi Chroma."""
    db = _get_chroma_db()
    try:
        db._collection.delete(where={"session_id": session_id})
    except Exception as e:
        print(f"[vectorstore] Error removing session {session_id}: {e}")
