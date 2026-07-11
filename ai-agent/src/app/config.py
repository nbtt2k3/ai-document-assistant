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
STORAGE_DIR = Path(os.environ.get("STORAGE_DIR", BASE_DIR / "storage"))
DATA_PATH = os.environ.get("DATA_PATH", str(STORAGE_DIR / "uploads"))
VECTORSTORE_PATH = os.environ.get("VECTORSTORE_PATH", str(STORAGE_DIR / "chroma_db"))
DOCSTORE_PATH = os.environ.get("DOCSTORE_PATH", str(STORAGE_DIR / "docstore"))
FLASHRANK_CACHE_PATH = os.environ.get("FLASHRANK_CACHE", str(BASE_DIR / "models" / "reranker"))

# Tạo thư mục nếu chưa tồn tại
Path(DATA_PATH).mkdir(parents=True, exist_ok=True)
Path(VECTORSTORE_PATH).mkdir(parents=True, exist_ok=True)
Path(DOCSTORE_PATH).mkdir(parents=True, exist_ok=True)
Path(FLASHRANK_CACHE_PATH).mkdir(parents=True, exist_ok=True)

# ── API Keys ──────────────────────────────────────────────────────────────────
# Ưu tiên theo thứ tự: GitHub → OpenRouter → Grok (xAI) → OpenAI → Gemini → Local
GITHUB_TOKEN       = os.environ.get("GITHUB_TOKEN", "")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
XAI_API_KEY = os.environ.get("XAI_API_KEY", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
LLAMA_CLOUD_API_KEY = os.environ.get("LLAMA_CLOUD_API_KEY", "")
COHERE_API_KEY = os.environ.get("COHERE_API_KEY", "")

# ── Online Model Names ────────────────────────────────────────────────────────
GITHUB_LLM_MODEL       = os.environ.get("GITHUB_LLM_MODEL", "gpt-4o")
OPENROUTER_LLM_MODEL   = os.environ.get("OPENROUTER_LLM_MODEL", "qwen/qwen3-coder:free")
XAI_LLM_MODEL          = os.environ.get("XAI_LLM_MODEL", "grok-beta")
GROQ_LLM_MODEL         = os.environ.get("GROQ_LLM_MODEL", "llama-3.3-70b-versatile")

OPENAI_LLM_MODEL       = os.environ.get("OPENAI_LLM_MODEL", "gpt-4o-mini")
OPENAI_EMBEDDING_MODEL = os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

GEMINI_LLM_MODEL       = os.environ.get("GEMINI_LLM_MODEL", "gemini-2.5-flash")
GEMINI_EMBEDDING_MODEL = os.environ.get("GEMINI_EMBEDDING_MODEL", "text-embedding-004")

# ── Local Model Names (Ollama) ────────────────────────────────────────────────
# HƯỚNG DẪN CHỌN MODEL CHO CẤU HÌNH MÁY (Sử dụng Ollama Local - mặc định khi không có API Key):
OLLAMA_BASE_URL  = os.environ.get("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
EMBEDDING_MODEL  = os.environ.get("OLLAMA_EMBEDDING_MODEL", "bge-m3")
LLM_MODEL        = os.environ.get("OLLAMA_LLM_MODEL", "llama3.1:8b")

# ── Text splitting ────────────────────────────────────────────────────────────
CHUNK_SIZE    = int(os.environ.get("CHUNK_SIZE", 800))
CHUNK_OVERLAP = int(os.environ.get("CHUNK_OVERLAP", 150))

# ── Retrieval tuning ──────────────────────────────────────────────────────────
# Số tài liệu giữ lại sau bước reranking (FlashrankRerank)
# Tăng nếu muốn LLM có nhiều ngữ cảnh hơn, giảm nếu muốn tiết kiệm token
RERANK_TOP_N  = int(os.environ.get("RERANK_TOP_N", 5))

# ── Upload limits ─────────────────────────────────────────────────────────────
# Kích thước file tối đa cho phép upload (đơn vị: MB)
MAX_FILE_SIZE_MB = int(os.environ.get("MAX_FILE_SIZE_MB", 50))

# ── CORS ────────────────────────────────────────────────────────────────────
# Service nội bộ — chỉ web-api và localhost mới cần gọi trực tiếp
# Trong production, không nên expose port 8001 ra ngoài
_raw_origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000,http://web-api:8000")
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]
