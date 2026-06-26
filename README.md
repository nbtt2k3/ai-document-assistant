# AI Document Assistant (RAG Chatbot)

Một hệ thống trợ lý ảo AI (Retrieval-Augmented Generation - RAG) cho phép bạn tải tài liệu lên (PDF, DOCX, TXT) và trò chuyện, đặt câu hỏi dựa trên nội dung tài liệu. Dự án này được thiết kế theo cấu trúc Client-Server, sử dụng các mô hình ngôn ngữ lớn (LLM) chạy hoàn toàn nội bộ thông qua **Ollama**, đảm bảo tính bảo mật dữ liệu tuyệt đối.

## 🚀 Tính năng nổi bật
- Tải và trích xuất nội dung từ nhiều loại tài liệu (PDF, Word).
- Trò chuyện tự nhiên với tài liệu (RAG).
- Chạy hoàn toàn cục bộ (Local) - Không cần Internet để xử lý dữ liệu.
- Hỗ trợ kết nối các API AI Online siêu nhanh (ChatGPT, Gemini).
- Lưu trữ lịch sử trò chuyện và quản lý các phiên chat (Sessions).
- Đề xuất câu hỏi tự động.

## 💻 Yêu cầu hệ thống (Prerequisites)
- [Python 3.10+](https://www.python.org/downloads/)
- [Node.js 18+](https://nodejs.org/)
- [Ollama](https://ollama.ai/) (Dùng để chạy AI Models cục bộ).

### Hướng dẫn chọn cấu hình Model (Tối ưu cho Phần cứng)
Mặc định hệ thống được cấu hình cho **Laptop/PC cấu hình phổ thông (Ví dụ: i5, RTX 3050 4GB VRAM, 16GB RAM)**.
Nếu cấu hình máy bạn khác, hãy xem `backend/src/app/rag/config.py` để tùy chỉnh:
- **Máy tính/Laptop yếu (VRAM < 4GB):** Dùng LLM `qwen2.5:1.5b` hoặc `llama3.2:1b`, Embedding `nomic-embed-text`.
- **Máy tầm trung (VRAM 6GB - 8GB):** Dùng LLM `qwen2.5:3b`, Embedding `bge-m3`.
- **Máy mạnh (VRAM > 12GB):** Dùng LLM `qwen2.5:7b`, Embedding `bge-m3`.

*(Trước khi chạy, hãy mở terminal và gõ `ollama run qwen2.5:1.5b` và `ollama pull nomic-embed-text` để tải model về máy)*.

### Sử dụng Online Models (ChatGPT, Gemini) thay cho Local
Nếu bạn muốn hệ thống trả lời siêu nhanh và thông minh hơn bằng các API trả phí/miễn phí của Google hoặc OpenAI:
1. Tạo một file tên là `.env` trong thư mục `backend/` (bạn có thể copy từ `.env.example`).
2. Điền API Key của bạn vào:
   ```env
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
   GEMINI_API_KEY=AIzaSyXxxxxxxxxxxxxxxx
   ```
*(Hệ thống sẽ tự động chuyển sang dùng mô hình tương ứng. Ưu tiên: OpenAI > Gemini > Ollama Local).*

---

## 🛠️ Hướng dẫn cài đặt

### 1. Cài đặt Backend (FastAPI + LangChain)
Mở terminal và di chuyển vào thư mục `backend`:
```bash
cd backend

# Tạo môi trường ảo (Virtual Environment)
python -m venv .venv

# Kích hoạt môi trường ảo
# Trên Windows:
.venv\Scripts\activate
# Trên macOS/Linux:
source .venv/bin/activate

# Cài đặt thư viện
pip install -r requirements.txt

# Chạy server
uvicorn src.app.api.main:app --reload
```
Backend sẽ chạy tại: `http://localhost:8000`

### 2. Cài đặt Frontend (Next.js)
Mở một terminal MỚI và di chuyển vào thư mục `frontend`:
```bash
cd frontend

# Cài đặt thư viện
npm install

# Chạy giao diện
npm run dev
```
Frontend sẽ chạy tại: `http://localhost:3000`

## 📂 Cấu trúc thư mục
- `/backend`: Chứa mã nguồn máy chủ, API, logic RAG, VectorStore (ChromaDB) và quản lý file.
- `/frontend`: Chứa giao diện người dùng viết bằng Next.js, React.

## 🤝 Đóng góp (Contributing)
Mọi đóng góp, báo lỗi (issues) và pull requests đều được hoan nghênh. Xin vui lòng tạo issue trước khi submit PR lớn.
