"""
ocr/registry.py — File loader registry.

Ánh xạ đuôi file → loader class.
Thêm định dạng mới chỉ cần import loader + thêm vào FILE_LOADERS dict.
"""
from langchain_community.document_loaders import TextLoader

from src.app.ocr.pdf_reader import CustomPDFLoader
from src.app.ocr.docx_reader import CustomDocxLoader


# Mapping: đuôi file → loader class
FILE_LOADERS: dict = {
    ".pdf":  CustomPDFLoader,
    ".txt":  TextLoader,
    ".docx": CustomDocxLoader,
}

SUPPORTED_EXTENSIONS = set(FILE_LOADERS.keys())
