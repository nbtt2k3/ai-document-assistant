"""
rag/embedder.py — Embedding abstraction.

Singleton OllamaEmbeddings. Đổi embedding provider chỉ cần sửa ở đây.

Ví dụ đổi sang OpenAI:
    from langchain_openai import OpenAIEmbeddings
    _embedder = OpenAIEmbeddings(model=EMBEDDING_MODEL)
"""
from langchain_ollama import OllamaEmbeddings

from src.app.rag.config import EMBEDDING_MODEL

# Singleton: khởi tạo một lần, dùng chung toàn app
_embedder = OllamaEmbeddings(model=EMBEDDING_MODEL)


def get_embedder() -> OllamaEmbeddings:
    """Trả về embedding model singleton."""
    return _embedder
