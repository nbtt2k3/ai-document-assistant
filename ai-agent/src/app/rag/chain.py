"""
rag/chain.py — LangChain RAG pipeline assembly.

Xây dựng Hybrid Retriever (BM25 + Vector) + LLM chain cho từng session.
Đây là trung tâm của RAG engine.

Các thành phần được import từ:
- prompts.py      : Prompt templates
- llm_factory.py  : LLM provider selection
- utils.py        : format_docs, clean_output, citations
"""
from operator import itemgetter
from typing import List

from langchain.retrievers import EnsembleRetriever
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables import RunnableBranch, RunnablePassthrough

from src.app.rag.prompts import (
    ROUTER_PROMPT_TEMPLATE,
    CHITCHAT_PROMPT_TEMPLATE,
    SUMMARIZE_PROMPT_TEMPLATE,
    TRANSLATE_PROMPT_TEMPLATE,
    RAG_PROMPT_TEMPLATE,
)
from src.app.rag.llm_factory import get_llm
from src.app.rag.utils import format_docs
from src.app.rag.vectorstore import get_retriever_for_session
from src.app.rag.bm25 import get_bm25_results


# ── BM25 Retriever wrapper ─────────────────────────────────────────────────────

class SessionBM25Retriever(BaseRetriever):
    """LangChain-compatible retriever wrapper cho BM25 per-session."""
    session_id: str

    def _get_relevant_documents(self, query: str, *, run_manager=None) -> List[Document]:
        return get_bm25_results(self.session_id, query, k=3)


# ── RAG Chain factory ─────────────────────────────────────────────────────────

def create_rag_chain_for_session(session_id: str, section_title: str = None, level: int = None):
    """Tạo Hybrid RAG chain (BM25 + Vector + LLM) riêng cho một session."""

    if section_title and level:
        from src.app.rag.vectorstore import get_retriever_for_section
        # Chỉ dùng vector retriever để lấy toàn bộ chunk của mục này
        retriever = get_retriever_for_section(session_id, section_title, level)
    else:
        # 1. Vector retriever (Chroma, filter theo session_id)
        vector_retriever = get_retriever_for_session(session_id)

        # 2. BM25 retriever (RAM-based, per-session)
        bm25_retriever = SessionBM25Retriever(session_id=session_id)

        # 3. Hybrid: 50% BM25 + 50% Vector
        retriever = EnsembleRetriever(
            retrievers=[bm25_retriever, vector_retriever],
            weights=[0.5, 0.5]
        )

    # Lấy LLM từ factory
    llm = get_llm()

    # Tạo prompt objects
    router_prompt = ChatPromptTemplate.from_template(ROUTER_PROMPT_TEMPLATE)
    chitchat_prompt = ChatPromptTemplate.from_template(CHITCHAT_PROMPT_TEMPLATE)
    summarize_prompt = ChatPromptTemplate.from_template(SUMMARIZE_PROMPT_TEMPLATE)
    translate_prompt = ChatPromptTemplate.from_template(TRANSLATE_PROMPT_TEMPLATE)
    rag_prompt = ChatPromptTemplate.from_template(RAG_PROMPT_TEMPLATE)

    # Router Chain (Output is a single word: RAG, CHITCHAT, SUMMARIZE, TRANSLATE)
    router_chain = router_prompt | llm | StrOutputParser() | (lambda x: x.strip().upper())

    # Branch Chains
    chitchat_chain = chitchat_prompt | llm | StrOutputParser()
    
    # Retrieve context for branches that need it
    context_retriever = itemgetter("question") | retriever | format_docs

    summarize_chain = (
        {"context": context_retriever, "question": itemgetter("question")}
        | summarize_prompt | llm | StrOutputParser()
    )
    
    translate_chain = (
        {"context": context_retriever, "question": itemgetter("question")}
        | translate_prompt | llm | StrOutputParser()
    )

    rag_chain = (
        {
            "context": context_retriever,
            "question": itemgetter("question"),
            "chat_history": itemgetter("chat_history"),
        }
        | rag_prompt
        | llm
        | StrOutputParser()
    )

    # Route using RunnableBranch
    branch = RunnableBranch(
        (lambda x: "CHITCHAT" in x["intent"], chitchat_chain),
        (lambda x: "SUMMARIZE" in x["intent"], summarize_chain),
        (lambda x: "TRANSLATE" in x["intent"], translate_chain),
        rag_chain
    )

    full_chain = (
        RunnablePassthrough.assign(intent=router_chain)
        | branch
    )

    return full_chain
