"""
ocr/image_reader.py — Đọc file ảnh (PNG, JPG, ...) thành Document.

Dùng OCR engine để trích xuất chữ từ ảnh.
"""
import os

from langchain_core.documents import Document

from src.app.ocr.engine import extract_text


class ImageOCRLoader:
    """Trích xuất văn bản từ file ảnh bằng OCR engine."""

    def __init__(self, file_path: str):
        self.file_path = file_path

    def load(self) -> list[Document]:
        basename = os.path.basename(self.file_path)
        print(f"  👁️  Đang quét ảnh: {basename}")
        print("      🔍 Đang nhận dạng chữ (OCR)...")

        ocr_text = extract_text(self.file_path)

        content = (
            f"[ẢNH: {basename}]\n"
            f"- Nội dung chữ trích xuất: {ocr_text}"
        )
        return [Document(
            page_content=content,
            metadata={"source": self.file_path, "page": 1}
        )]
