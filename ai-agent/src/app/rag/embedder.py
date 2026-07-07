"""
rag/embedder.py — Embedding abstraction.

Singleton embedding model. Hỗ trợ OpenAI, Gemini, và Ollama.
"""
from langchain_ollama import OllamaEmbeddings
from langchain_openai import OpenAIEmbeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from src.app.config import (
    EMBEDDING_MODEL, OLLAMA_BASE_URL,
    OPENAI_API_KEY, OPENAI_EMBEDDING_MODEL,
    GEMINI_API_KEY, GEMINI_EMBEDDING_MODEL
)

# Khởi tạo embedder linh hoạt (Singleton pattern)
_embedder = None

def get_embedder():
    """Trả về embedding model dựa trên API key có sẵn."""
    global _embedder
    if _embedder is not None:
        return _embedder

    if OPENAI_API_KEY:
        print(f"[INFO] Dang su dung Embedder Online: OpenAI ({OPENAI_EMBEDDING_MODEL})")
        _embedder = OpenAIEmbeddings(
            model=OPENAI_EMBEDDING_MODEL,
            api_key=OPENAI_API_KEY
        )
    elif GEMINI_API_KEY:
        print(f"[INFO] Dang su dung Embedder Online: Gemini ({GEMINI_EMBEDDING_MODEL})")
        _embedder = GoogleGenerativeAIEmbeddings(
            model=f"models/{GEMINI_EMBEDDING_MODEL}",
            google_api_key=GEMINI_API_KEY
        )
    else:
        print(f"[INFO] Dang su dung Embedder Local: Ollama ({EMBEDDING_MODEL})")
        _embedder = OllamaEmbeddings(
            model=EMBEDDING_MODEL, 
            base_url=OLLAMA_BASE_URL
        )

    return _embedder
