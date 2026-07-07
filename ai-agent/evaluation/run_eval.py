import os
import json
import sys
from pathlib import Path

# Thêm thư mục root vào sys.path để có thể import từ src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
)
from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings

def main():
    # Load biến môi trường (Lấy OPENAI_API_KEY)
    load_dotenv(Path(__file__).parent.parent / ".env")
    
    if not os.environ.get("OPENAI_API_KEY"):
        print("\n[LỖI] Không tìm thấy OPENAI_API_KEY trong file .env.")
        print("Vui lòng cấu hình OPENAI_API_KEY để Ragas sử dụng GPT-4 làm Giám khảo (LLM-as-a-judge).\n")
        return

    # Khởi tạo mô hình đánh giá (GPT-4o mini cho nhanh và rẻ)
    eval_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.0)
    eval_embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

    # Đọc dữ liệu mẫu
    data_path = Path(__file__).parent / "sample_data.json"
    print(f"Đang đọc dữ liệu từ: {data_path}")
    
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Chuyển đổi dữ liệu sang định dạng Dataset của HuggingFace
    dataset_dict = {
        "question": [item["question"] for item in data],
        "answer": [item["answer"] for item in data],
        "contexts": [item["contexts"] for item in data],
        "ground_truth": [item.get("ground_truth", "") for item in data],
    }
    
    dataset = Dataset.from_dict(dataset_dict)
    
    print("\nBắt đầu chấm điểm bằng Ragas (Quá trình này có thể mất 1-2 phút)...\n")
    
    # Định cấu hình các số đo
    metrics = [
        faithfulness,
        answer_relevancy,
        context_precision,
        context_recall,
    ]
    
    # Bắt đầu đánh giá
    result = evaluate(
        dataset=dataset,
        metrics=metrics,
        llm=eval_llm,
        embeddings=eval_embeddings,
    )
    
    # In kết quả
    print("================ KẾT QUẢ ĐÁNH GIÁ (RAGAS) ================")
    print(result)
    print("==========================================================")
    
    # Lưu kết quả chi tiết ra file CSV
    out_csv = Path(__file__).parent / "evaluation_results.csv"
    df = result.to_pandas()
    df.to_csv(out_csv, index=False, encoding="utf-8")
    
    print(f"\n[THÀNH CÔNG] Chi tiết điểm số từng câu hỏi đã được lưu vào: {out_csv}")
    print("\nGiải thích các chỉ số:")
    print("- faithfulness (Độ trung thực): AI có bịa chuyện (ảo giác) không? 1.0 là hoàn hảo.")
    print("- answer_relevancy (Độ bám sát): Câu trả lời có đúng trọng tâm câu hỏi không?")
    print("- context_precision: Tài liệu được trích xuất có chuẩn xác và nằm ở top đầu không?")
    print("- context_recall: Tài liệu được trích xuất có bao phủ đủ thông tin để trả lời không?")

if __name__ == "__main__":
    main()
