"""
rag/config.py — Cấu hình AI/RAG Engine (thuần AI, không có OCR).

Cấu hình OCR nằm ở: src/app/ocr/config.py
Cấu hình hạ tầng web nằm ở: src/app/core/config.py
"""

import os

# ── LLM & Embedding ───────────────────────────────────────────────────────────
# Các biến cấu hình cho Online Models (ưu tiên theo thứ tự OpenAI -> Gemini -> Local)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

OPENAI_LLM_MODEL = os.environ.get("OPENAI_LLM_MODEL", "gpt-4o-mini")
OPENAI_EMBEDDING_MODEL = os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

GEMINI_LLM_MODEL = os.environ.get("GEMINI_LLM_MODEL", "gemini-2.5-flash")
GEMINI_EMBEDDING_MODEL = os.environ.get("GEMINI_EMBEDDING_MODEL", "gemini-embedding-2")

# HƯỚNG DẪN CHỌN MODEL CHO CẤU HÌNH MÁY (Sử dụng Ollama Local - mặc định khi không có API Key):

EMBEDDING_MODEL = "bge-m3"
LLM_MODEL       = "qwen3:4b"

# ── Text splitting ────────────────────────────────────────────────────────────
CHUNK_SIZE    = 800
CHUNK_OVERLAP = 150
