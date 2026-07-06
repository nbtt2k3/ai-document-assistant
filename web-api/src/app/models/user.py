"""
models/user.py — SQLAlchemy model cho bảng users.
"""
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from src.app.db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    sessions = relationship("Session", back_populates="owner")
