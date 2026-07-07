from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from src.app.api import router
from src.app.config import ALLOWED_ORIGINS

app = FastAPI(title="AI Agent API")

app.add_middleware(
    CORSMiddleware,
    # Fix 8: Dùng ALLOWED_ORIGINS từ config thay vì allow_origins=["*"]
    # Có thể override qua env ALLOWED_ORIGINS=http://domain1.com,http://domain2.com
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.get("/")
def root():
    return {"message": "AI Agent Service is running"}

if __name__ == "__main__":
    uvicorn.run("src.app.main:app", host="0.0.0.0", port=8001, reload=True)
