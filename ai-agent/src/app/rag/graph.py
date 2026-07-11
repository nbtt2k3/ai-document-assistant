"""
rag/graph.py — CRAG (Self-Corrective RAG) implementation using LangGraph.
"""
from typing import TypedDict, List, Literal
from langgraph.graph import StateGraph, END
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field
import asyncio
import logging
from src.app.prompts.prompt_manager import PromptManager
from src.app.rag.utils import format_docs
from src.app.rag.vectorstore import get_all_parent_documents
from src.app.rag.llm_factory import get_llm

class RouteIntent(BaseModel):
    intent: Literal["RAG", "CHITCHAT", "SUMMARIZE", "TRANSLATE"] = Field(
        description="The classified intent of the user's question."
    )
    target_filename: str = Field(
        description="The specific filename the user is asking about, if mentioned. Otherwise empty string.", 
        default=""
    )


class GraphState(TypedDict):
    session_id: str
    question: str
    chat_history: str
    intent: str
    target_filename: str
    documents: List[Document]
    generation: str
    retries: int

def create_crag_graph(session_id: str, section_title: str = None, level: int = None):
    llm = get_llm()
    from src.app.rag.chain import get_base_retriever

    async def route_question(state: GraphState):
        raw_messages = PromptManager.get_langchain_messages("router")
        
        # 1. Thử dùng chuẩn Function Calling (Tốt nhất cho mô hình lớn như GPT-4, Llama 70B)
        try:
            prompt_fc = ChatPromptTemplate.from_messages(raw_messages)
            chain_fc = prompt_fc | llm.with_structured_output(RouteIntent)
            result = await chain_fc.ainvoke({"question": state["question"], "chat_history": state["chat_history"]})
            intent = result.intent
            target_filename = result.target_filename
            
        except Exception as e_fc:
            logging.warning(f"[ROUTER] Function Calling thất bại ({e_fc}), tự động chuyển sang JsonOutputParser...")
            
            # 2. Fallback sang JsonOutputParser (Trâu bò nhất cho mô hình nhỏ như Llama 8B, Ollama)
            try:
                from langchain_core.output_parsers import JsonOutputParser
                parser = JsonOutputParser(pydantic_object=RouteIntent)
                system_msg = raw_messages[0][1] + "\n\n{format_instructions}\nBẮT BUỘC TRẢ VỀ CHUẨN JSON."
                prompt_json = ChatPromptTemplate.from_messages([
                    ("system", system_msg),
                    ("human", raw_messages[1][1])
                ])
                chain_json = prompt_json | llm | parser
                result_dict = await chain_json.ainvoke({
                    "question": state["question"], 
                    "chat_history": state["chat_history"],
                    "format_instructions": parser.get_format_instructions()
                })
                intent = result_dict.get("intent", "RAG")
                target_filename = result_dict.get("target_filename", "")
                
            except Exception as e_json:
                logging.error(f"[ROUTER] JsonOutputParser cũng thất bại ({e_json}), fallback về cấu hình an toàn.")
                # 3. Fallback cuối cùng: Đảm bảo hệ thống không bao giờ sập (Crash)
                intent = "RAG"
                target_filename = ""
                
        logging.info(f"[ROUTER] Question: '{state['question']}' -> Intent: {intent}, TargetFile: {target_filename}")
        return {"intent": intent, "target_filename": target_filename}

    async def retrieve(state: GraphState):
        target_filename = state.get("target_filename", "")
        retriever = get_base_retriever(session_id, section_title, level, target_filename)
        documents = await retriever.ainvoke(state["question"])
        return {"documents": documents}

    async def grade_documents(state: GraphState):
        documents = state.get("documents", [])
        if not documents:
            # Không tìm được chunk nào → thử rewrite query nếu chưa đạt max retry
            retries = state.get("retries", 0)
            if retries < 2:
                logging.info(f"[CRAG] Không có tài liệu, thử rewrite query (retry {retries + 1}/2)")
                return {"intent": "REWRITE"}
            # Đã retry đủ → generate với context rỗng, LLM sẽ từ chối lịch sự
            logging.info("[CRAG] Không tìm được tài liệu sau 2 lần rewrite, generate với context rỗng")
            return {"intent": "GENERATE"}
            
        prompt = ChatPromptTemplate.from_messages(PromptManager.get_langchain_messages("grade_document"))
        chain = prompt | llm | StrOutputParser()
        context = format_docs(documents)
        score = await chain.ainvoke({"question": state["question"], "context": context})
        
        logging.info(f"[CRAG] Đánh giá tài liệu: {score.strip().lower()}")
        if "yes" in score.strip().lower():
            return {"intent": "GENERATE"}
        else:
            return {"intent": "REWRITE"}

    async def rewrite_query(state: GraphState):
        prompt = ChatPromptTemplate.from_messages(PromptManager.get_langchain_messages("rewrite_query"))
        chain = prompt | llm | StrOutputParser()
        new_question = await chain.ainvoke({"question": state["question"], "chat_history": state["chat_history"]})
        new_question = new_question.strip()
        logging.info(f"[CRAG] Đã viết lại câu hỏi: '{state['question']}' -> '{new_question}'")
        retries = state.get("retries", 0) + 1
        return {"question": new_question, "retries": retries}

    async def generate_rag(state: GraphState, config: RunnableConfig):
        prompt = ChatPromptTemplate.from_messages(PromptManager.get_langchain_messages("rag"))
        chain = prompt | llm.with_config(tags=["final_generation"]) | StrOutputParser()
        context = format_docs(state.get("documents", []))
        generation = await chain.ainvoke({
            "context": context,
            "question": state["question"],
            "chat_history": state["chat_history"]
        }, config)
        return {"generation": generation}

    async def chitchat_node(state: GraphState, config: RunnableConfig):
        prompt = ChatPromptTemplate.from_messages(PromptManager.get_langchain_messages("chitchat"))
        chain = prompt | llm.with_config(tags=["final_generation"]) | StrOutputParser()
        generation = await chain.ainvoke({"question": state["question"], "chat_history": state["chat_history"]}, config)
        return {"generation": generation}

    async def summarize_node(state: GraphState, config: RunnableConfig):
        logging.info(f"[CRAG] Bắt đầu Map-Reduce Summarize cho session {session_id}")
        target_filename = state.get("target_filename", "")
        docs = get_all_parent_documents(session_id, target_filename)
        
        if not docs:
            return {"generation": "Không tìm thấy tài liệu nào để tóm tắt."}
            
        map_prompt = ChatPromptTemplate.from_messages(PromptManager.get_langchain_messages("map_summary"))
        map_chain = map_prompt | llm | StrOutputParser()
        
        sem = asyncio.Semaphore(2)
        
        async def _map_doc(doc):
            async with sem:
                source_name = doc.metadata.get('source', 'Unknown').split('/')[-1]
                context = f"[Trang {doc.metadata.get('page', 0)} - {source_name}]\n{doc.page_content}"
                for attempt in range(3):
                    try:
                        res = await map_chain.ainvoke({"context": context, "question": state["question"]}, config)
                        # Tránh spam API dồn dập
                        await asyncio.sleep(2)
                        return (source_name, res.strip())
                    except Exception as e:
                        if "429" in str(e) or "Rate limit" in str(e):
                            logging.warning(f"[CRAG] Rate limit hit, sleeping for 30s... (Attempt {attempt+1}/3)")
                            await asyncio.sleep(30)
                        else:
                            logging.error(f"[CRAG] Map error: {e}")
                            return (source_name, "")
                return (source_name, "")
                
        map_results = await asyncio.gather(*[_map_doc(doc) for doc in docs])
        
        # Nhóm các summary theo filename để truyền cho Reduce
        from collections import defaultdict
        grouped_summaries = defaultdict(list)
        for source_name, res in map_results:
            if res and "IGNORE" not in res.upper():
                grouped_summaries[source_name].append(res)
        
        if not grouped_summaries:
            return {"generation": "Không tìm thấy nội dung nào khớp với yêu cầu tóm tắt của bạn trong tài liệu."}
            
        combined_parts = []
        for source_name, summaries in grouped_summaries.items():
            combined_parts.append(f"### Tóm tắt từ file: {source_name}\n" + "\n".join(summaries))
            
        combined_summaries = "\n\n---\n\n".join(combined_parts)
        
        reduce_prompt = ChatPromptTemplate.from_messages(PromptManager.get_langchain_messages("reduce_summary"))
        reduce_chain = reduce_prompt | llm.with_config(tags=["final_generation"]) | StrOutputParser()
        
        final_summary = await reduce_chain.ainvoke({"summaries": combined_summaries, "question": state["question"]}, config)
        return {"generation": final_summary, "documents": docs}

    async def translate_node(state: GraphState, config: RunnableConfig):
        prompt = ChatPromptTemplate.from_messages(PromptManager.get_langchain_messages("translate"))
        chain = prompt | llm.with_config(tags=["final_generation"]) | StrOutputParser()
        context = format_docs(state.get("documents", []))
        generation = await chain.ainvoke({"question": state["question"], "chat_history": state["chat_history"], "context": context}, config)
        return {"generation": generation}

    def router_condition(state: GraphState):
        intent = state["intent"]
        if "CHITCHAT" in intent: return "chitchat"
        if "SUMMARIZE" in intent: return "summarize"
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
    workflow.add_node("summarize", summarize_node)
    workflow.add_node("retrieve_for_translate", retrieve)
    workflow.add_node("translate", translate_node)

    workflow.set_entry_point("route_question")
    
    workflow.add_conditional_edges("route_question", router_condition)
    
    workflow.add_edge("retrieve", "grade_documents")
    workflow.add_conditional_edges("grade_documents", grade_condition)
    workflow.add_edge("rewrite_query", "retrieve")
    
    workflow.add_edge("chitchat", END)
    
    workflow.add_edge("summarize", END)
    
    workflow.add_edge("retrieve_for_translate", "translate")
    workflow.add_edge("translate", END)
    
    workflow.add_edge("generate_rag", END)

    return workflow.compile()
