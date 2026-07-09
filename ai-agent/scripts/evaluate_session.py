import os
import sys
import asyncio
import psycopg2
from psycopg2.extras import DictCursor
import json
from datetime import datetime

# Đảm bảo có thể import code từ ai-agent
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

# Thông số kết nối DB
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "rag_user")
DB_PASS = os.getenv("DB_PASS", "rag_password")
DB_NAME = os.getenv("DB_NAME", "rag_db")

def get_session_messages(session_id=None):
    """Lấy danh sách các cặp QA từ database."""
    conn = None
    try:
        conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASS, database=DB_NAME
        )
        cur = conn.cursor(cursor_factory=DictCursor)
        
        # Nếu không truyền session_id, lấy session mới nhất
        if not session_id:
            cur.execute("SELECT id FROM sessions ORDER BY created_at DESC LIMIT 1")
            row = cur.fetchone()
            if not row:
                print("❌ Không tìm thấy phiên chat nào trong database.")
                return []
            session_id = row['id']
            print(f"👉 Không truyền Session ID. Tự động đánh giá phiên mới nhất: {session_id}")
        else:
            print(f"👉 Đánh giá phiên chat: {session_id}")
            
        # Lấy tất cả tin nhắn của session
        cur.execute("""
            SELECT role, content, sources 
            FROM messages 
            WHERE session_id = %s 
            ORDER BY created_at ASC, id ASC
        """, (session_id,))
        
        messages = cur.fetchall()
        
        qa_pairs = []
        current_q = None
        
        for msg in messages:
            # Bỏ qua tin nhắn hệ thống (upload file)
            if msg['content'].startswith("**") and msg['content'].endswith("**"):
                continue
                
            if msg['role'] == 'user':
                current_q = msg['content']
            elif msg['role'] == 'bot' and current_q:
                # Xử lý sources (nếu có)
                sources = msg['sources'] if msg['sources'] else []
                if isinstance(sources, str):
                    try:
                        sources = json.loads(sources)
                    except:
                        pass
                        
                context_str = ""
                if isinstance(sources, list):
                    context_parts = []
                    for s in sources:
                        text = s.get('text', '') if isinstance(s, dict) else str(s)
                        if text:
                            context_parts.append(text)
                    context_str = "\n".join(context_parts)
                
                qa_pairs.append({
                    "question": current_q,
                    "answer": msg['content'],
                    "context": context_str
                })
                current_q = None # Reset
                
        return qa_pairs
    except Exception as e:
        print(f"❌ Lỗi kết nối DB: {e}")
        return []
    finally:
        if conn:
            conn.close()

async def evaluate_pair(qa, llm, prompt):
    """Đánh giá 1 cặp QA."""
    chain = prompt | llm | JsonOutputParser()
    try:
        score = await chain.ainvoke({
            "question": qa["question"],
            "context": qa["context"] if qa["context"] else "(Không có tài liệu truy xuất)",
            "answer": qa["answer"]
        })
        return score
    except Exception as e:
        print(f"  [!] Lỗi đánh giá 1 câu: {e}")
        return {"faithfulness": 0.0, "answer_relevancy": 0.0}

async def main():
    if not os.environ.get("GROQ_API_KEY"):
        print("❌ LỖI: Chưa có GROQ_API_KEY trong environment.")
        print("Mẹo: Mở file docker-compose.yml, hoặc export GROQ_API_KEY=xxx trên terminal trước khi chạy.")
        return

    session_id = sys.argv[1] if len(sys.argv) > 1 else None
    
    qa_pairs = get_session_messages(session_id)
    
    if not qa_pairs:
        print("Không có câu hỏi/trả lời nào để đánh giá.")
        return
        
    print(f"🔍 Tìm thấy {len(qa_pairs)} cặp Hỏi - Đáp. Bắt đầu chấm điểm bằng Llama-3.1-70B...\n")
    
    eval_llm = ChatGroq(
        model_name="llama-3.3-70b-versatile", 
        temperature=0.0,
        model_kwargs={"response_format": {"type": "json_object"}},
        max_retries=5,
    )
    eval_prompt = ChatPromptTemplate.from_template('''Bạn là một giám khảo chuyên gia chấm điểm hệ thống RAG (Retrieval-Augmented Generation).
Hãy đọc CÂU HỎI, TÀI LIỆU, và CÂU TRẢ LỜI bên dưới, sau đó chấm điểm từ 0.0 đến 1.0 cho 2 tiêu chí sau:
1. "faithfulness": Độ trung thực. Câu trả lời có được rút ra trực tiếp từ TÀI LIỆU không? (AI được phép diễn đạt lại bằng từ đồng nghĩa hoặc giải thích logic, ví dụ: "không để cùng nơi" -> "để riêng biệt". Không trừ điểm vì việc diễn đạt lại này). Tuy nhiên, nếu AI tự bịa ra một hướng dẫn hoặc quy trình không hề có trong tài liệu, phải phạt nặng (0.0 - 0.5). Nếu AI từ chối trả lời vì tài liệu thiếu thông tin, hãy cho 1.0. 
2. "answer_relevancy": Độ bám sát. Câu trả lời có giải quyết đúng trọng tâm CÂU HỎI không? Nếu câu hỏi không thể trả lời từ tài liệu và AI từ chối, hãy cho 1.0. (1.0 = Rất đúng trọng tâm/từ chối đúng, 0.0 = Lạc đề).

CÂU HỎI: {question}
TÀI LIỆU: {context}
CÂU TRẢ LỜI: {answer}

QUAN TRỌNG: Bạn PHẢI suy luận (reasoning) cẩn thận trước khi đưa ra điểm số. 
Trả về KẾT QUẢ DƯỚI DẠNG JSON với chính xác 5 trường (fields) sau:
{{
  "is_chitchat": <boolean: true nếu CÂU HỎI chỉ là chào hỏi, cảm ơn, hoặc giao tiếp xã giao thuần túy không hỏi thông tin>,
  "reasoning_faithfulness": "<Giải thích tại sao bạn chấm điểm faithfulness như vậy>",
  "faithfulness": <float từ 0.0 đến 1.0>,
  "reasoning_relevancy": "<Giải thích tại sao bạn chấm điểm answer_relevancy như vậy>",
  "answer_relevancy": <float từ 0.0 đến 1.0>
}}
''')

    total_faith = 0
    total_rel = 0
    evaluated_count = 0
    
    for i, qa in enumerate(qa_pairs, 1):
        print(f"Đang chấm điểm câu {i}/{len(qa_pairs)}...")
        print(f" Q: {qa['question']}")
        
        scores = await evaluate_pair(qa, eval_llm, eval_prompt)
        
        if scores.get("is_chitchat", False):
            print(" => Bỏ qua chấm điểm vì đây là câu hỏi giao tiếp xã giao (Chitchat).\n")
            continue
            
        faith = float(scores.get("faithfulness", 0.0))
        rel = float(scores.get("answer_relevancy", 0.0))
        reasoning_faith = scores.get("reasoning_faithfulness", "")
        reasoning_rel = scores.get("reasoning_relevancy", "")
        
        total_faith += faith
        total_rel += rel
        evaluated_count += 1
        
        print(f" => Faithfulness: {faith:.2f} | Relevancy: {rel:.2f}")
        if reasoning_faith or reasoning_rel:
            print(f"    [Lý do] Faithfulness: {reasoning_faith}")
            print(f"    [Lý do] Relevancy   : {reasoning_rel}\n")
        else:
            print("\n")
        
    # Tổng kết
    if evaluated_count == 0:
        print("Không có câu hỏi RAG nào để chấm điểm (toàn bộ là Chitchat).")
        return
        
    avg_faith = total_faith / evaluated_count
    avg_rel = total_rel / evaluated_count
    
    print("=" * 60)
    print(" 🏆 BÁO CÁO TỔNG HỢP (BATCH EVALUATION)")
    print("=" * 60)
    print(f" Số lượng câu hỏi RAG đã chấm : {evaluated_count} / {len(qa_pairs)}")
    print(f" Trung bình Độ trung thực     : {avg_faith:.2f} / 1.00")
    print(f" Trung bình Độ bám sát        : {avg_rel:.2f} / 1.00")
    print("=" * 60)
    
    if avg_faith < 0.8:
        print("\n⚠️ CẢNH BÁO: Độ trung thực quá thấp. Cần kiểm tra lại System Prompt để chống ảo giác.")
    if avg_rel < 0.8:
        print("\n⚠️ CẢNH BÁO: AI đang trả lời hơi lạc đề so với câu hỏi.")

if __name__ == "__main__":
    asyncio.run(main())
