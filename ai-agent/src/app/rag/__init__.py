"""
rag/ — AI/RAG Engine package (thuần AI logic).

KHÔNG chứa OCR (→ xem src/app/ocr/)
KHÔNG biết về FastAPI, JWT, DB (→ xem src/app/api/)

Modules:
- prompts.py     : Prompt templates (Router, Chitchat, Summarize, Translate, RAG)
- llm_factory.py : LLM provider selection (OpenAI → Gemini → Ollama)
- utils.py       : format_docs, clean_output, citation tracking
- embedder.py    : Embedding singleton (dễ swap provider)
- vectorstore.py : ChromaDB — lưu trữ & tìm kiếm vector
- bm25.py        : BM25 keyword search (in-memory, per-session)
- chain.py       : LangChain Hybrid RAG pipeline assembly (query → answer)
"""
