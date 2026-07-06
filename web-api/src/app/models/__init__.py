"""
Models package — SQLAlchemy ORM models.

Để SQLAlchemy nhận biết tất cả models trước khi gọi Base.metadata.create_all(),
tất cả models phải được import tại đây.

Import cũ (backward compatible):
    from src.app.models.models import User, Session, Message

Import mới (khuyến nghị):
    from src.app.models import User, Session, Message
    # hoặc theo entity:
    from src.app.models.user import User
    from src.app.models.session import Session
    from src.app.models.message import Message
"""
from .user import User
from .session import Session
from .message import Message

__all__ = ["User", "Session", "Message"]
