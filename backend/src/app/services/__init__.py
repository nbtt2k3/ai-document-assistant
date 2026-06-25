"""
services/ — Orchestration Layer.

Lớp trung gian giữa API (api/) và các engine (rag/, ocr/).
API chỉ gọi services, không gọi thẳng vào RAG hay OCR.

Modules:
- document_service.py : upload file → OCR → index vào RAG
- chat_service.py     : câu hỏi → RAG chain → stream kết quả
"""
