"""
core/config.py — Cấu hình Web App.

Chứa các hằng số liên quan đến hạ tầng web:
- Đường dẫn storage (uploads, vectorstore)
- Load biến môi trường từ .env

Cấu hình AI/ML (model names, OCR) nằm ở: src/app/rag/config.py
"""
import os
import logging
from pathlib import Path

# ── Tắt telemetry spam của ChromaDB ──────────────────────────────────────────
os.environ["ANONYMIZED_TELEMETRY"] = "False"
logging.getLogger("chromadb.telemetry").setLevel(logging.CRITICAL)
logging.getLogger("chromadb").setLevel(logging.ERROR)

from dotenv import load_dotenv
load_dotenv()

# ── Đường dẫn gốc ────────────────────────────────────────────────────────────
# __file__ = backend/src/app/core/config.py → parents[3] = backend/
BASE_DIR = Path(__file__).resolve().parents[3]

# ── Đường dẫn storage runtime ─────────────────────────────────────────────────
# Tất cả dữ liệu runtime nằm trong storage/ (đã có trong .gitignore)
STORAGE_DIR      = BASE_DIR / "storage"
DATA_PATH        = str(STORAGE_DIR / "uploads")
VECTORSTORE_PATH = str(STORAGE_DIR / "chroma_db")

# Tạo thư mục nếu chưa tồn tại
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
(STORAGE_DIR / "uploads").mkdir(parents=True, exist_ok=True)
(STORAGE_DIR / "chroma_db").mkdir(parents=True, exist_ok=True)
