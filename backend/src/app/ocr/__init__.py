"""
ocr/ — OCR Engine package.

Tách hoàn toàn khỏi RAG. Chịu trách nhiệm duy nhất:
trích xuất văn bản từ file (ảnh, PDF, DOCX, TXT).

Modules:
- config.py       : Cấu hình OCR (engine, ngôn ngữ, GPU)
- engine.py       : Singleton OCR reader + unified extract_text() interface
- image_reader.py : Đọc ảnh PNG/JPG → Document
- pdf_reader.py   : Đọc PDF/DOCX/TXT → list[Document]
"""
