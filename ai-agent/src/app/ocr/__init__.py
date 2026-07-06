"""
ocr/ — OCR Engine package.

Tách hoàn toàn khỏi RAG. Chịu trách nhiệm duy nhất:
trích xuất văn bản từ file (ảnh, PDF, DOCX, TXT).

Modules:
- engine.py       : Singleton OCR reader + unified extract_text() interface
- image_reader.py : Đọc ảnh PNG/JPG → Document
- pdf_reader.py   : Đọc PDF → list[Document]
- docx_reader.py  : Đọc DOCX → list[Document]
- registry.py     : FILE_LOADERS mapping (đuôi file → loader class)
"""
