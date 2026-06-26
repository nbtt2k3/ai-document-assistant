# AI Document Assistant

Một hệ thống trợ lý ảo AI (Retrieval-Augmented Generation - RAG) toàn diện, cho phép tải tài liệu lên (PDF, DOCX) và trò chuyện dựa trên nội dung tài liệu. Dự án được thiết kế theo kiến trúc Client-Server (Next.js + FastAPI), tích hợp sẵn xác thực người dùng, lưu trữ lịch sử chat, và khả năng đọc hiểu cả các tài liệu scan bằng công nghệ nhận dạng ký tự quang học (OCR).

## 🚀 Tính năng nổi bật
- **Bảo mật người dùng:** Tích hợp tính năng Đăng nhập/Đăng ký với JWT Token, mỗi người dùng có không gian lưu trữ và lịch sử chat riêng biệt.
- **Quản lý Phiên (Sessions):** Lưu trữ toàn bộ lịch sử các cuộc trò chuyện và tài liệu vào cơ sở dữ liệu PostgreSQL.
- **RAG Nâng cao (Hybrid Retrieval):** Kết hợp cả tìm kiếm theo từ khóa (BM25) và tìm kiếm ngữ nghĩa (ChromaDB Vector Store) để cho ra kết quả chính xác nhất.
- **Trích xuất thông minh (OCR):** Tích hợp công nghệ PaddleOCR giúp đọc và trích xuất chữ từ cả các tệp PDF dạng scan hoặc hình ảnh.
- **Linh hoạt Mô hình AI:**
  - **Local (Riêng tư 100%):** Hỗ trợ chạy các LLM mã nguồn mở qua Ollama (Qwen, Llama).
  - **Online (Siêu tốc):** Hỗ trợ kết nối các API mạnh mẽ của ChatGPT (OpenAI) và Gemini (Google).
- **LangSmith Tracing:** Tích hợp sẵn theo dõi luồng dữ liệu LangChain để debug dễ dàng.

## 💻 Yêu cầu hệ thống (Prerequisites)
- [Python 3.10+](https://www.python.org/downloads/)
- [Node.js 18+](https://nodejs.org/)
- [PostgreSQL](https://www.postgresql.org/download/) (Chạy local hoặc qua Docker).
- [Ollama](https://ollama.ai/) (Nếu bạn muốn chạy AI Models cục bộ).

---

## ⚙️ Cấu hình Môi trường (.env)

Tạo một file `.env` ở thư mục `backend/` dựa trên file `.env.example` và thiết lập các thông số:
1. **Database:** Cập nhật `DATABASE_URL` trỏ tới database PostgreSQL của bạn.
2. **Bảo mật:** Đổi `SECRET_KEY` thành một chuỗi bảo mật ngẫu nhiên.
3. **API Keys (Tùy chọn):** 
   - Điền `OPENAI_API_KEY` hoặc `GEMINI_API_KEY` nếu bạn muốn dùng model online (sẽ bỏ qua Ollama).
   - Điền `LANGCHAIN_API_KEY` để theo dõi các truy vấn RAG qua LangSmith.

### Gợi ý cấu hình Local Model (Cho Ollama)
Nếu bạn **không dùng API Key**, hệ thống sẽ chạy Ollama. Hãy chỉnh `backend/src/app/rag/config.py` cho hợp với máy bạn:
- **Laptop yếu (VRAM < 4GB):** Dùng LLM `qwen2.5:1.5b` hoặc `llama3.2:1b`, Embedding `nomic-embed-text`.
- **Máy tầm trung (VRAM 6GB - 8GB):** Dùng LLM `qwen2.5:3b`, Embedding `bge-m3`.
- **Máy mạnh (VRAM > 12GB):** Dùng LLM `qwen2.5:7b`, Embedding `bge-m3`.

*(Mở terminal gõ `ollama run qwen2.5:1.5b` và `ollama pull nomic-embed-text` để tải model trước khi chạy)*.

---

## 🛠️ Hướng dẫn cài đặt

### 1. Cài đặt Backend (FastAPI + LangChain)
Mở terminal và di chuyển vào thư mục `backend`:
```bash
cd backend

# Tạo môi trường ảo (Virtual Environment)
python -m venv .venv

# Kích hoạt môi trường ảo (Windows)
.venv\Scripts\activate
# Trên macOS/Linux: source .venv/bin/activate

# Cài đặt thư viện
pip install -r requirements.txt

# Chạy server
uvicorn src.app.main:app --reload --port 8000
```
API sẽ chạy tại: `http://localhost:8000` (Truy cập `http://localhost:8000/docs` để xem Swagger UI).

### 2. Cài đặt Frontend (Next.js)
Mở một terminal MỚI và di chuyển vào thư mục `frontend`:
```bash
cd frontend

# Cài đặt thư viện
npm install

# Chạy giao diện
npm run dev
```
Giao diện sẽ chạy tại: `http://localhost:3000`

## 📂 Cấu trúc dự án
- `/backend/src/app`:
  - `api/`: Định nghĩa các API endpoints (auth, sessions, chat).
  - `models/`: Định nghĩa các bảng Database (SQLAlchemy).
  - `ocr/`: Module xử lý trích xuất văn bản & hình ảnh.
  - `rag/`: Module xử lý LangChain (Chain, VectorStore, Embedder, BM25).
- `/frontend/src`:
  - `app/`: Giao diện các trang Next.js.
  - `components/`: UI Components (ChatWindow, Sidebar, v.v.).
  - `hooks/`: Custom hooks để gọi API.

## 🤝 Đóng góp (Contributing)
Mọi đóng góp, báo lỗi (issues) và pull requests đều được hoan nghênh. Xin vui lòng tạo issue trước khi submit PR.
