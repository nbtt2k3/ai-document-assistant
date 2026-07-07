"""
core/config.py — Cấu hình Web App.

Chứa các hằng số liên quan đến hạ tầng web và kết nối AI Agent.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Đường dẫn gốc ────────────────────────────────────────────────────────────
# __file__ = backend/src/app/core/config.py → parents[3] = backend/
BASE_DIR = Path(__file__).resolve().parents[3]

# Cấu hình AI Agent URL (mặc định cho Docker Compose)
AI_AGENT_URL = os.getenv("AI_AGENT_URL", "http://ai-agent:8001")

# Cấu hình CORS
ALLOWED_ORIGINS_STR = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
ALLOWED_ORIGINS = [origin.strip() for origin in ALLOWED_ORIGINS_STR.split(",") if origin.strip()]
