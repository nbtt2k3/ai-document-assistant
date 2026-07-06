"""
schemas/auth.py — Pydantic schemas cho Authentication endpoints.
"""
from pydantic import BaseModel


class UserCreate(BaseModel):
    """Body request để đăng ký tài khoản mới."""
    username: str
    password: str


class Token(BaseModel):
    """Response trả về sau khi đăng nhập thành công."""
    access_token: str
    token_type: str
