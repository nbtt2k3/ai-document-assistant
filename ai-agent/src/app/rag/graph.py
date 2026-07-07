"""
rag/graph.py — CRAG (Self-Corrective RAG) implementation using LangGraph.
"""
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableConfig

from src.app.rag.llm_factory import get_llm
from src.app.rag.prompts import (
    ROUTER_PROMPT_TEMPLATE,
    CHITCHAT_PROMPT_TEMPLATE,
    SUMMARIZE_PROMPT_TEMPLATE,
    TRANSLATE_PROMPT_TEMPLATE,
    RAG_SYSTEM_PROMPT,
    RAG_HUMAN_PROMPT,
    GRADE_DOCUMENT_PROMPT_TEMPLATE,
    REWRITE_QUERY_PROMPT_TEMPLATE
)
from src.app.rag.utils import format_docs

class GraphState(TypedDict):
    session_id: str
    question: str
    chat_history: str
    intent: str
    documents: List[Document]
    generation: str
    retries: int

def create_crag_graph(session_id: str, section_title: str = None, level: int = None):
    llm = get_llm()
    from src.app.rag.chain import get_base_retriever
    retriever = get_base_retriever(session_id, section_title, level)

    async def route_question(state: GraphState):
        prompt = ChatPromptTemplate.from_template(ROUTER_PROMPT_TEMPLATE)
        chain = prompt | llm | StrOutputParser()
        intent = await chain.ainvoke({"question": state["question"], "chat_history": state["chat_history"]})
        return {"intent": intent.strip().upper()}

    async def retrieve(state: GraphState):
        documents = await retriever.ainvoke(state["question"])
        return {"documents": documents}

    async def grade_documents(state: GraphState):
        documents = state.get("documents", [])
        if not documents:
            # Không tìm được chunk nào → thử rewrite query nếu chưa đạt max retry
            retries = state.get("retries", 0)
            if retries < 2:
                print(f"[CRAG] Không có tài liệu, thử rewrite query (retry {retries + 1}/2)")
                return {"intent": "REWRITE"}
            # Đã retry đủ → generate với context rỗng, LLM sẽ từ chối lịch sự
            print("[CRAG] Không tìm được tài liệu sau 2 lần rewrite, generate với context rỗng")
            return {"intent": "GENERATE"}
            
        prompt = ChatPromptTemplate.from_template(GRADE_DOCUMENT_PROMPT_TEMPLATE)
        chain = prompt | llm | StrOutputParser()
        context = format_docs(documents)
        score = await chain.ainvoke({"question": state["question"], "context": context})
        
        print(f"[CRAG] Đánh giá tài liệu: {score.strip().lower()}")
        if "yes" in score.strip().lower():
            return {"intent": "GENERATE"}
        else:
            return {"intent": "REWRITE"}

    async def rewrite_query(state: GraphState):
        prompt = ChatPromptTemplate.from_template(REWRITE_QUERY_PROMPT_TEMPLATE)
        chain = prompt | llm | StrOutputParser()
        new_question = await chain.ainvoke({"question": state["question"], "chat_history": state["chat_history"]})
        new_question = new_question.strip()
        print(f"[CRAG] Đã viết lại câu hỏi: '{state['question']}' -> '{new_question}'")
        retries = state.get("retries", 0) + 1
        return {"question": new_question, "retries": retries}

    async def generate_rag(state: GraphState, config: RunnableConfig):
        prompt = ChatPromptTemplate.from_messages([("system", RAG_SYSTEM_PROMPT), ("human", RAG_HUMAN_PROMPT)])
        chain = prompt | llm.with_config(tags=["final_generation"]) | StrOutputParser()
        context = format_docs(state.get("documents", []))
        generation = await chain.ainvoke({
            "context": context,
            "question": state["question"],
            "chat_history": state["chat_history"]
        }, config)
        return {"generation": generation}

    async def chitchat_node(state: GraphState, config: RunnableConfig):
        prompt = ChatPromptTemplate.from_template(CHITCHAT_PROMPT_TEMPLATE)
        chain = prompt | llm.with_config(tags=["final_generation"]) | StrOutputParser()
        generation = await chain.ainvoke({"question": state["question"], "chat_history": state["chat_history"]}, config)
        return {"generation": generation}

    async def summarize_node(state: GraphState, config: RunnableConfig):
        prompt = ChatPromptTemplate.from_template(SUMMARIZE_PROMPT_TEMPLATE)
        chain = prompt | llm.with_config(tags=["final_generation"]) | StrOutputParser()
        context = format_docs(state.get("documents", []))
        generation = await chain.ainvoke({"question": state["question"], "chat_history": state["chat_history"], "context": context}, config)
        return {"generation": generation}

    async def translate_node(state: GraphState, config: RunnableConfig):
        prompt = ChatPromptTemplate.from_template(TRANSLATE_PROMPT_TEMPLATE)
        chain = prompt | llm.with_config(tags=["final_generation"]) | StrOutputParser()
        context = format_docs(state.get("documents", []))
        generation = await chain.ainvoke({"question": state["question"], "chat_history": state["chat_history"], "context": context}, config)
        return {"generation": generation}

    def router_condition(state: GraphState):
        intent = state["intent"]
        if "CHITCHAT" in intent: return "chitchat"
        if "SUMMARIZE" in intent: return "retrieve_for_summarize"
        if "TRANSLATE" in intent: return "retrieve_for_translate"
        return "retrieve"

    def grade_condition(state: GraphState):
        if state["intent"] == "REWRITE" and state.get("retries", 0) < 2:
            return "rewrite_query"
        return "generate_rag"

    workflow = StateGraph(GraphState)
    workflow.add_node("route_question", route_question)
    
    workflow.add_node("retrieve", retrieve)
    workflow.add_node("grade_documents", grade_documents)
    workflow.add_node("rewrite_query", rewrite_query)
    workflow.add_node("generate_rag", generate_rag)
    
    workflow.add_node("chitchat", chitchat_node)
    workflow.add_node("retrieve_for_summarize", retrieve)
    workflow.add_node("summarize", summarize_node)
    workflow.add_node("retrieve_for_translate", retrieve)
    workflow.add_node("translate", translate_node)

    workflow.set_entry_point("route_question")
    
    workflow.add_conditional_edges("route_question", router_condition)
    
    workflow.add_edge("retrieve", "grade_documents")
    workflow.add_conditional_edges("grade_documents", grade_condition)
    workflow.add_edge("rewrite_query", "retrieve")
    
    workflow.add_edge("chitchat", END)
    
    workflow.add_edge("retrieve_for_summarize", "summarize")
    workflow.add_edge("summarize", END)
    
    workflow.add_edge("retrieve_for_translate", "translate")
    workflow.add_edge("translate", END)
    
    workflow.add_edge("generate_rag", END)

    return workflow.compile()
