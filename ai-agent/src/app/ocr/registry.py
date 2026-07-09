"""
ocr/registry.py — File loader registry.

Ánh xạ đuôi file → loader class.
Thêm định dạng mới chỉ cần import loader + thêm vào FILE_LOADERS dict.
"""
from langchain_community.document_loaders import TextLoader

from src.app.ocr.pdf_reader import CustomPDFLoader
from src.app.ocr.docx_reader import CustomDocxLoader
from src.app.ocr.markitdown_reader import MarkItDownLoader
from src.app.ocr.image_reader import ImageOCRLoader
from src.app.ocr.excel_reader import CustomExcelLoader


class Utf8TextLoader:
    """
    Wrapper cho TextLoader với encoding UTF-8 và autodetect.
    Tránh lỗi khi đọc file .txt tiếng Việt có encoding khác hệ thống.
    """
    def __init__(self, file_path: str):
        self._loader = TextLoader(file_path, encoding="utf-8", autodetect_encoding=True)

    def load(self):
        return self._loader.load()


FILE_LOADERS: dict = {
    ".pdf":  CustomPDFLoader,
    ".txt":  Utf8TextLoader,
    ".docx": CustomDocxLoader,
    ".xlsx": CustomExcelLoader,
    ".csv":  CustomExcelLoader,
    ".png":  ImageOCRLoader,
    ".jpg":  ImageOCRLoader,
    ".jpeg": ImageOCRLoader,
}

SUPPORTED_EXTENSIONS = set(FILE_LOADERS.keys())
