"""
models/models.py — DEPRECATED.

File này được giữ lại để đảm bảo tương thích ngược (backward compatibility).
Vui lòng dùng import trực tiếp từ các module entity:

    from src.app.models.user import User
    from src.app.models.session import Session
    from src.app.models.message import Message

hoặc từ package:

    from src.app.models import User, Session, Message
"""
from src.app.models.user import User
from src.app.models.session import Session
from src.app.models.message import Message

__all__ = ["User", "Session", "Message"]
