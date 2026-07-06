from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

load_dotenv()

# Lấy cấu hình DB từ .env, nếu không có thì mặc định dùng thông số của Docker Compose
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://rag_user:rag_password@localhost:5432/rag_db"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
