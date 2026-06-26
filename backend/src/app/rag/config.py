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

GEMINI_LLM_MODEL = os.environ.get("GEMINI_LLM_MODEL", "gemini-1.5-flash")
GEMINI_EMBEDDING_MODEL = os.environ.get("GEMINI_EMBEDDING_MODEL", "text-embedding-004")

# HƯỚNG DẪN CHỌN MODEL CHO CẤU HÌNH MÁY (Sử dụng Ollama Local - mặc định khi không có API Key):
# - Máy yếu / Laptop (VRAM < 4GB): Dùng LLM "qwen2.5:1.5b", "llama3.2:1b". Embedding "nomic-embed-text".
# - Máy tầm trung (VRAM 6GB - 8GB): Dùng LLM "qwen2.5:3b", "llama3.1:8b". Embedding "bge-m3".
# - Máy mạnh (VRAM > 12GB): Dùng LLM "qwen2.5:7b" hoặc "qwen3:14b". Embedding "bge-m3".

EMBEDDING_MODEL = "nomic-embed-text"
LLM_MODEL       = "qwen2.5:1.5b"

# ── Text splitting ────────────────────────────────────────────────────────────
CHUNK_SIZE    = 800
CHUNK_OVERLAP = 150
