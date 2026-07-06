"""
rag/llm_factory.py — LLM provider selection.

Chọn LLM dựa trên API key có sẵn:
  OpenAI → Gemini → Ollama (local)

Dùng chung cho chain.py và có thể mở rộng cho các use case khác.
"""
from langchain_ollama import OllamaLLM
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

from src.app.config import (
    LLM_MODEL, OLLAMA_BASE_URL,
    OPENAI_API_KEY, OPENAI_LLM_MODEL,
    GEMINI_API_KEY, GEMINI_LLM_MODEL
)
from src.app.rag.prompts import STOP_SEQUENCES


def get_llm():
    """Trả về LLM instance dựa trên cấu hình API key có sẵn."""
    if OPENAI_API_KEY:
        print(f"[INFO] Dang su dung LLM Online: OpenAI ({OPENAI_LLM_MODEL})")
        return ChatOpenAI(
            model=OPENAI_LLM_MODEL,
            api_key=OPENAI_API_KEY,
            temperature=0.0,
            stop=STOP_SEQUENCES,
        )
    elif GEMINI_API_KEY:
        print(f"[INFO] Dang su dung LLM Online: Gemini ({GEMINI_LLM_MODEL})")
        return ChatGoogleGenerativeAI(
            model=GEMINI_LLM_MODEL,
            google_api_key=GEMINI_API_KEY,
            temperature=0.0,
            stop=STOP_SEQUENCES,
        )
    else:
        print(f"[INFO] Dang su dung LLM Local: Ollama ({LLM_MODEL})")
        return OllamaLLM(
            model=LLM_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0.0,
            stop=STOP_SEQUENCES,
        )
