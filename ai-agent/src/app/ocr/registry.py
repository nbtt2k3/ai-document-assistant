"""
ocr/registry.py — File loader registry.

Ánh xạ đuôi file → loader class.
Thêm định dạng mới chỉ cần import loader + thêm vào FILE_LOADERS dict.
"""
from langchain_community.document_loaders import TextLoader

from src.app.ocr.pdf_reader import CustomPDFLoader
from src.app.ocr.docx_reader import CustomDocxLoader
from src.app.ocr.markitdown_reader import MarkItDownLoader


FILE_LOADERS: dict = {
    ".pdf":  CustomPDFLoader,
    ".txt":  TextLoader,
    ".docx": CustomDocxLoader,
    ".xlsx": MarkItDownLoader,
    ".csv":  MarkItDownLoader,
}

SUPPORTED_EXTENSIONS = set(FILE_LOADERS.keys())
