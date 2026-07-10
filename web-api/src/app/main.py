from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from src.app.db.database import engine, Base
# Import tất cả models để SQLAlchemy đăng ký đầy đủ trước khi create_all
from src.app.models import User, Session as DBSession, Message  # noqa: F401
from src.app.api import auth, sessions, chat

from src.app.core.config import ALLOWED_ORIGINS, ALLOWED_ORIGIN_REGEX
from src.app.core.rate_limit import limiter
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

# Tạo các bảng DB nếu chưa có (bao bọc try/except để app không crash khi DB chưa sẵn sàng)
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"[WARNING] Không thể kết nối DB để tạo bảng: {e}")
    print("[WARNING] Hãy đảm bảo PostgreSQL đang chạy và DATABASE_URL trong .env là đúng.")

app = FastAPI(title="AI Document Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=ALLOWED_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(auth.router)
app.include_router(sessions.router)
app.include_router(chat.router)

@app.get("/")
def root():
    return {"message": "Welcome to AI Document Assistant API"}

if __name__ == "__main__":
    uvicorn.run("src.app.main:app", host="127.0.0.1", port=8000, reload=True)
