"""
config.py — Cấu hình tập trung cho toàn bộ AI Agent.

Gộp tất cả cấu hình vào một nơi duy nhất:
- Biến môi trường (.env)
- Đường dẫn storage (uploads, vectorstore)
- Cấu hình AI/ML (model names, API keys, chunk sizes)
- Cấu hình Ollama
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
# __file__ = ai-agent/src/app/config.py → parents[2] = ai-agent/
BASE_DIR = Path(__file__).resolve().parents[2]

# ── Đường dẫn storage runtime ─────────────────────────────────────────────────
# Tất cả dữ liệu runtime nằm trong storage/ (đã có trong .gitignore)
STORAGE_DIR      = BASE_DIR / "storage"
DATA_PATH        = str(STORAGE_DIR / "uploads")
VECTORSTORE_PATH = str(STORAGE_DIR / "chroma_db")

# Tạo thư mục nếu chưa tồn tại
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
(STORAGE_DIR / "uploads").mkdir(parents=True, exist_ok=True)
(STORAGE_DIR / "chroma_db").mkdir(parents=True, exist_ok=True)

# ── API Keys ──────────────────────────────────────────────────────────────────
# Ưu tiên theo thứ tự: GitHub → OpenRouter → Grok (xAI) → OpenAI → Gemini → Local
GITHUB_TOKEN       = os.environ.get("GITHUB_TOKEN", "")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
XAI_API_KEY = os.environ.get("XAI_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# ── Online Model Names ────────────────────────────────────────────────────────
GITHUB_LLM_MODEL       = os.environ.get("GITHUB_LLM_MODEL", "gpt-4o")
OPENROUTER_LLM_MODEL   = os.environ.get("OPENROUTER_LLM_MODEL", "qwen/qwen3-coder:free")
XAI_LLM_MODEL          = os.environ.get("XAI_LLM_MODEL", "grok-beta")

OPENAI_LLM_MODEL       = os.environ.get("OPENAI_LLM_MODEL", "gpt-4o-mini")

GEMINI_LLM_MODEL       = os.environ.get("GEMINI_LLM_MODEL", "gemini-2.5-flash")

# ── Local Model Names (Ollama) ────────────────────────────────────────────────
# HƯỚNG DẪN CHỌN MODEL CHO CẤU HÌNH MÁY (Sử dụng Ollama Local - mặc định khi không có API Key):
OLLAMA_BASE_URL  = os.environ.get("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
EMBEDDING_MODEL  = "bge-m3"
LLM_MODEL        = "qwen3:4b"

# ── Text splitting ────────────────────────────────────────────────────────────
CHUNK_SIZE    = 800
CHUNK_OVERLAP = 150
