"""
rag/llm_factory.py — LLM provider selection.

Chọn LLM dựa trên API key có sẵn:
  GitHub → OpenRouter → xAI (Grok) → Groq → OpenAI → Gemini → Ollama (local)

Singleton pattern: chỉ tạo LLM instance một lần để tránh CUDA OOM với Ollama local
khi pipeline gọi get_llm() nhiều lần trong một request.
"""
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_xai import ChatXAI
from langchain_groq import ChatGroq

from src.app.config import (
    LLM_MODEL, OLLAMA_BASE_URL,
    GITHUB_TOKEN, GITHUB_LLM_MODEL,
    OPENROUTER_API_KEY, OPENROUTER_LLM_MODEL,
    XAI_API_KEY, XAI_LLM_MODEL,
    GROQ_API_KEY, GROQ_LLM_MODEL,
    OPENAI_API_KEY, OPENAI_LLM_MODEL,
    GEMINI_API_KEY, GEMINI_LLM_MODEL
)
from src.app.prompts.base_prompt import STOP_SEQUENCES


# ── LLM Singleton ─────────────────────────────────────────────────────────────
_llm_instance = None


def is_online_llm() -> bool:
    """Kiểm tra xem đang dùng API online hay Ollama local."""
    return bool(GITHUB_TOKEN or OPENROUTER_API_KEY or XAI_API_KEY or GROQ_API_KEY or OPENAI_API_KEY or GEMINI_API_KEY)


def get_llm():
    """
    Trả về LLM singleton instance dựa trên cấu hình API key có sẵn.

    Singleton pattern đảm bảo chỉ có 1 LLM instance trong suốt vòng đời app,
    tránh tạo nhiều CUDA context gây OOM với Ollama local.
    """
    global _llm_instance
    if _llm_instance is not None:
        return _llm_instance

    if GITHUB_TOKEN:
        print(f"[INFO] Dang su dung LLM Online: GitHub Models ({GITHUB_LLM_MODEL})")
        _llm_instance = ChatOpenAI(
            model=GITHUB_LLM_MODEL,
            api_key=GITHUB_TOKEN,
            base_url="https://models.inference.ai.azure.com",
            temperature=0.0,
            stop=STOP_SEQUENCES,
        )
    elif OPENROUTER_API_KEY:
        print(f"[INFO] Dang su dung LLM Online: OpenRouter ({OPENROUTER_LLM_MODEL})")
        _llm_instance = ChatOpenAI(
            model=OPENROUTER_LLM_MODEL,
            api_key=OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
            temperature=0.0,
            stop=STOP_SEQUENCES,
        )
    elif XAI_API_KEY:
        print(f"[INFO] Dang su dung LLM Online: Grok (xAI) ({XAI_LLM_MODEL})")
        _llm_instance = ChatXAI(
            model=XAI_LLM_MODEL,
            xai_api_key=XAI_API_KEY,
            temperature=0.0,
            stop=STOP_SEQUENCES,
        )
    elif GROQ_API_KEY:
        print(f"[INFO] Dang su dung LLM Online: Groq ({GROQ_LLM_MODEL})")
        _llm_instance = ChatGroq(
            model=GROQ_LLM_MODEL,
            groq_api_key=GROQ_API_KEY,
            temperature=0.0,
            stop=STOP_SEQUENCES,
            max_retries=5,
        )
    elif OPENAI_API_KEY:
        print(f"[INFO] Dang su dung LLM Online: OpenAI ({OPENAI_LLM_MODEL})")
        _llm_instance = ChatOpenAI(
            model=OPENAI_LLM_MODEL,
            api_key=OPENAI_API_KEY,
            temperature=0.0,
            stop=STOP_SEQUENCES,
        )
    elif GEMINI_API_KEY:
        print(f"[INFO] Dang su dung LLM Online: Gemini ({GEMINI_LLM_MODEL})")
        _llm_instance = ChatGoogleGenerativeAI(
            model=GEMINI_LLM_MODEL,
            google_api_key=GEMINI_API_KEY,
            temperature=0.0,
            stop=STOP_SEQUENCES,
        )
    else:
        print(f"[INFO] Dang su dung LLM Local: Ollama ({LLM_MODEL})")
        _llm_instance = ChatOllama(
            model=LLM_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0.0,
            stop=STOP_SEQUENCES,
        )

    return _llm_instance

def get_vision_llm():
    """
    Trả về Vision LLM dựa trên cấu hình API key có sẵn.
    Dùng để đọc hiểu hình ảnh/biểu đồ thay cho OCR.
    """
    if OPENAI_API_KEY:
        return ChatOpenAI(model="gpt-4o-mini", api_key=OPENAI_API_KEY, temperature=0.0)
    elif GEMINI_API_KEY:
        return ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=GEMINI_API_KEY, temperature=0.0)
    # elif GROQ_API_KEY:
    #     return ChatGroq(model="llama-3.2-11b-vision-preview", groq_api_key=GROQ_API_KEY, temperature=0.0)
    elif GITHUB_TOKEN:
        return ChatOpenAI(model="gpt-4o", api_key=GITHUB_TOKEN, base_url="https://models.inference.ai.azure.com", temperature=0.0)
    
    return None
