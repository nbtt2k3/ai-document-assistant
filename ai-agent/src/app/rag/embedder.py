"""
rag/embedder.py — Embedding abstraction.

Singleton embedding model. Đổi embedding provider chỉ cần sửa ở đây.

Ví dụ đổi sang OpenAI:
    from langchain_openai import OpenAIEmbeddings
    _embedder = OpenAIEmbeddings(model=EMBEDDING_MODEL)
"""
from langchain_ollama import OllamaEmbeddings

from src.app.config import (
    EMBEDDING_MODEL, OLLAMA_BASE_URL
)

# Khởi tạo embedder linh hoạt (Singleton pattern)
_embedder = None

def get_embedder():
    """Trả về embedding model cục bộ bằng Ollama."""
    global _embedder
    if _embedder is not None:
        return _embedder

    print(f"[INFO] Dang su dung Embedder Local: Ollama ({EMBEDDING_MODEL})")
    _embedder = OllamaEmbeddings(
        model=EMBEDDING_MODEL, 
        base_url=OLLAMA_BASE_URL
    )

    return _embedder
