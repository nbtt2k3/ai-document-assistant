# AI Document Assistant

AI Document Assistant là hệ thống hỏi đáp tài liệu theo kiến trúc RAG. Người dùng có thể upload tài liệu, hệ thống sẽ trích xuất nội dung, index vào vector store/BM25, rồi trả lời câu hỏi dựa trên tài liệu đó.

## Thành Phần

- `frontend`: giao diện Next.js.
- `web-api`: FastAPI public API, auth, sessions, chat history, PostgreSQL.
- `ai-agent`: FastAPI internal service cho OCR, parsing, embedding, retrieval, LLM/RAG.
- `db`: PostgreSQL khi chạy bằng Docker Compose.

## Tính Năng Chính

- Đăng ký, đăng nhập, JWT auth.
- Quản lý session và lịch sử chat.
- Upload tài liệu và hỏi đáp theo nội dung.
- Hybrid retrieval: ChromaDB vector search + BM25 keyword search.
- OCR/parsing cho PDF, DOCX, Excel, text và ảnh.
- Hỗ trợ Ollama local và nhiều provider online qua API key.

## Cấu Trúc Thư Mục

```text
.
├── ai-agent/          # OCR, parsing, embedding, vectorstore, RAG graph
├── frontend/          # Next.js UI
├── web-api/           # Public API, auth, DB, session/chat orchestration
├── docker-compose.yml
├── ENVIRONMENT.md
└── README.md
```

## Environment

Mỗi service có một file env mẫu riêng:

- `ai-agent/.env.example`
- `web-api/.env.example`
- `frontend/.env.example`

Tạo env local:

```powershell
Copy-Item ai-agent\.env.example ai-agent\.env
Copy-Item web-api\.env.example web-api\.env
Copy-Item frontend\.env.example frontend\.env.local
```

Ghi chú:

- File `.env` thật không được commit.
- `ai-agent/.env` và `ai-agent/.env.example` dùng cùng cấu trúc section.
- `web-api/.env` và `web-api/.env.example` dùng cùng cấu trúc section.
- Xem thêm [ENVIRONMENT.md](ENVIRONMENT.md) nếu cần biết biến nào thuộc service nào.

## Chạy Bằng Docker Compose

Yêu cầu:

- Docker Desktop
- Ollama nếu muốn chạy local model trên máy host

Chạy toàn bộ stack:

```powershell
docker compose up --build
```

Các endpoint mặc định:

- Frontend: `http://localhost:3000`
- Web API: `http://localhost:8000`
- AI Agent: `http://localhost:8001`
- Postgres host port: `5433`

Trong Docker Compose:

- `web-api` gọi Postgres qua `db:5432`.
- `web-api` gọi `ai-agent` qua `http://ai-agent:8001`.
- `ai-agent` gọi Ollama trên host qua `http://host.docker.internal:11434`.

## Chạy Local Từng Service

### Web API

```powershell
cd web-api
pip install -r requirements.txt
uvicorn src.app.main:app --reload --port 8000
```

### AI Agent

```powershell
cd ai-agent
pip install -r requirements.txt
uvicorn src.app.main:app --reload --port 8001
```

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

## Runtime Data

Các thư mục/file runtime này có thể xuất hiện trong `ai-agent/`:

- `storage/`
- `flashrank_cache/`
- file zip model rerank
- `__pycache__/`

Chúng được giữ ngoài git bằng `.gitignore`. Riêng `storage`, `flashrank_cache`, và zip model vẫn hiện trong VSCode để dễ kiểm tra dữ liệu runtime.

## Ghi Chú Bảo Mật

- Không commit `.env` thật.
- Đổi `SECRET_KEY` trước khi deploy production.
- Chỉ điền API key cho provider bạn thật sự dùng.
- Nếu không có API key online, hệ thống sẽ fallback về Ollama local theo cấu hình trong `ai-agent/.env`.
