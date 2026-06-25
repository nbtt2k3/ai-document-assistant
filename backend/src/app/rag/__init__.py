"""
rag/ — AI/RAG Engine package (thuần AI logic).

KHÔNG chứa OCR (→ xem src/app/ocr/)
KHÔNG biết về FastAPI, JWT, DB (→ xem src/app/api/, src/app/core/)

Modules:
- config.py      : EMBEDDING_MODEL, LLM_MODEL, CHUNK_SIZE
- embedder.py    : Embedding singleton (dễ swap provider)
- vectorstore.py : ChromaDB — lưu trữ & tìm kiếm vector
- bm25.py        : BM25 keyword search (in-memory, per-session)
- chain.py       : LangChain Hybrid RAG pipeline (query → answer)
"""
