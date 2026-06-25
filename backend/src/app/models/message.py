"""
models/message.py — SQLAlchemy model cho bảng messages.
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from src.app.db.database import Base


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("sessions.id"))
    role = Column(String(20), nullable=False)  # "user" hoặc "bot"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("Session", back_populates="messages")
