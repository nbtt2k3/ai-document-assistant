"""
schemas/session.py — Pydantic schemas cho Sessions & Messages endpoints.
"""
from pydantic import BaseModel
from datetime import datetime


class SessionCreate(BaseModel):
    """Body request để tạo session mới."""
    title: str


class SessionResponse(BaseModel):
    """Response trả về thông tin một session."""
    id: str
    title: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    """Response trả về một tin nhắn trong session."""
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}
