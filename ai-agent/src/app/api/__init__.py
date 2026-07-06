"""
api/ — HTTP Routes package.

Chứa các route files, mỗi file phụ trách một nhóm endpoint.
Tất cả routers được đăng ký vào `router` chung tại __init__.py.

Modules:
- document_routes.py : Upload tài liệu & lấy TOC
- chat_routes.py     : Chat streaming (SSE)
- session_routes.py  : Quản lý session (cleanup)
"""
from fastapi import APIRouter

from src.app.api.document_routes import router as document_router
from src.app.api.chat_routes import router as chat_router
from src.app.api.session_routes import router as session_router

router = APIRouter(prefix="/internal", tags=["Internal"])

router.include_router(document_router)
router.include_router(chat_router)
router.include_router(session_router)
