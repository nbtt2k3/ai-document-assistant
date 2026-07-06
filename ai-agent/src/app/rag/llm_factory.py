"""
rag/llm_factory.py — LLM provider selection.

Chọn LLM dựa trên API key có sẵn:
  OpenAI → Gemini → Ollama (local)

Dùng chung cho chain.py và có thể mở rộng cho các use case khác.
"""
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_xai import ChatXAI

from src.app.config import (
    LLM_MODEL, OLLAMA_BASE_URL,
    GITHUB_TOKEN, GITHUB_LLM_MODEL,
    OPENROUTER_API_KEY, OPENROUTER_LLM_MODEL,
    XAI_API_KEY, XAI_LLM_MODEL,
    OPENAI_API_KEY, OPENAI_LLM_MODEL,
    GEMINI_API_KEY, GEMINI_LLM_MODEL
)
from src.app.rag.prompts import STOP_SEQUENCES


def get_llm():
    """Trả về LLM instance dựa trên cấu hình API key có sẵn."""
    if GITHUB_TOKEN:
        print(f"[INFO] Dang su dung LLM Online: GitHub Models ({GITHUB_LLM_MODEL})")
        return ChatOpenAI(
            model=GITHUB_LLM_MODEL,
            api_key=GITHUB_TOKEN,
            base_url="https://models.inference.ai.azure.com",
            temperature=0.0,
            stop=STOP_SEQUENCES,
        )
    elif OPENROUTER_API_KEY:
        print(f"[INFO] Dang su dung LLM Online: OpenRouter ({OPENROUTER_LLM_MODEL})")
        return ChatOpenAI(
            model=OPENROUTER_LLM_MODEL,
            api_key=OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
            temperature=0.0,
            stop=STOP_SEQUENCES,
        )
    elif XAI_API_KEY:
        print(f"[INFO] Dang su dung LLM Online: Grok (xAI) ({XAI_LLM_MODEL})")
        return ChatXAI(
            model=XAI_LLM_MODEL,
            xai_api_key=XAI_API_KEY,
            temperature=0.0,
            stop=STOP_SEQUENCES,
        )
    elif OPENAI_API_KEY:
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
        return ChatOllama(
            model=LLM_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0.0,
            stop=STOP_SEQUENCES,
        )
