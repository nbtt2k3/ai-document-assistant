"""
services/document_service.py — Orchestration cho việc xử lý tài liệu.

Điều phối toàn bộ pipeline:
  File upload → Lưu disk → Parse (OCR) → Index (RAG vectorstore + BM25)

API layer chỉ cần gọi process_upload() và cleanup_session_data(),
không cần biết OCR hay RAG hoạt động như thế nào.
"""
import os
import shutil
from pathlib import Path

from langchain_core.documents import Document

from src.app.core.config import DATA_PATH
from src.app.ocr.pdf_reader import FILE_LOADERS, SUPPORTED_EXTENSIONS
from src.app.rag.vectorstore import add_documents_to_session, remove_documents_for_session
from src.app.rag.bm25 import build_bm25_for_session, remove_bm25_for_session


def get_supported_extensions() -> set:
    """Trả về tập hợp các đuôi file được hỗ trợ."""
    return SUPPORTED_EXTENSIONS


def process_upload(session_id: str, file_path: str, filename: str) -> int:
    """
    Parse tài liệu và index vào RAG engine.

    Args:
        session_id : ID của session sở hữu tài liệu.
        file_path  : Đường dẫn tuyệt đối đến file đã được lưu trên disk.
        filename   : Tên gốc của file (để lấy extension).

    Returns:
        Số lượng đoạn văn (segments) đã được index thành công.

    Raises:
        ValueError  : Nếu đuôi file không được hỗ trợ.
        RuntimeError: Nếu quá trình parse hoặc index thất bại.
    """
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Định dạng file '{ext}' không được hỗ trợ. "
                         f"Hỗ trợ: {', '.join(sorted(SUPPORTED_EXTENSIONS))}")

    loader_class = FILE_LOADERS[ext]
    docs: list[Document] = loader_class(file_path).load()

    if docs:
        # 1. Index vào Chroma (vector search)
        add_documents_to_session(session_id, docs)
        # 2. Build BM25 index (keyword search)
        build_bm25_for_session(session_id, docs)

    return len(docs)


def save_upload_file(session_id: str, filename: str, content: bytes) -> str:
    """
    Lưu file upload vào disk.

    Returns:
        Đường dẫn tuyệt đối của file đã lưu.
    """
    session_dir = os.path.join(DATA_PATH, session_id)
    os.makedirs(session_dir, exist_ok=True)
    file_path = os.path.join(session_dir, filename)
    with open(file_path, "wb") as f:
        f.write(content)
    return file_path


def cleanup_session_data(session_id: str):
    """
    Dọn dẹp toàn bộ dữ liệu liên quan đến một session:
    - Xóa file vật lý trên disk
    - Xóa vectors khỏi ChromaDB
    - Xóa BM25 index khỏi RAM
    """
    # 1. File vật lý
    session_dir = os.path.join(DATA_PATH, session_id)
    if os.path.exists(session_dir):
        shutil.rmtree(session_dir, ignore_errors=True)

    # 2. Chroma vectors
    remove_documents_for_session(session_id)

    # 3. BM25 RAM index
    remove_bm25_for_session(session_id)
