"""
schemas/chat.py — Pydantic schemas cho Chat endpoints.
"""
from pydantic import BaseModel


class ChatRequest(BaseModel):
    """Body request để gửi câu hỏi tới chatbot."""
    question: str
