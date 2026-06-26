"""
rag/config.py — Cấu hình AI/RAG Engine (thuần AI, không có OCR).

Cấu hình OCR nằm ở: src/app/ocr/config.py
Cấu hình hạ tầng web nằm ở: src/app/core/config.py
"""

# ── LLM & Embedding ───────────────────────────────────────────────────────────
EMBEDDING_MODEL = "bge-m3"
LLM_MODEL       = "qwen3:4b"

# ── Text splitting ────────────────────────────────────────────────────────────
CHUNK_SIZE    = 800
CHUNK_OVERLAP = 150
