"""
rag/embedder.py — Embedding abstraction.

Singleton OllamaEmbeddings. Đổi embedding provider chỉ cần sửa ở đây.

Ví dụ đổi sang OpenAI:
    from langchain_openai import OpenAIEmbeddings
    _embedder = OpenAIEmbeddings(model=EMBEDDING_MODEL)
"""
from langchain_ollama import OllamaEmbeddings
from langchain_openai import OpenAIEmbeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from src.app.rag.config import (
    EMBEDDING_MODEL,
    OPENAI_API_KEY, OPENAI_EMBEDDING_MODEL,
    GEMINI_API_KEY, GEMINI_EMBEDDING_MODEL
)

# Khởi tạo embedder linh hoạt (Singleton pattern)
_embedder = None

def get_embedder():
    """Trả về embedding model dựa trên cấu hình API key có sẵn."""
    global _embedder
    if _embedder is not None:
        return _embedder

    if OPENAI_API_KEY:
        _embedder = OpenAIEmbeddings(
            model=OPENAI_EMBEDDING_MODEL,
            api_key=OPENAI_API_KEY
        )
    elif GEMINI_API_KEY:
        _embedder = GoogleGenerativeAIEmbeddings(
            model=f"models/{GEMINI_EMBEDDING_MODEL}",
            google_api_key=GEMINI_API_KEY
        )
    else:
        # Fallback to local Ollama
        _embedder = OllamaEmbeddings(model=EMBEDDING_MODEL)

    return _embedder
