"""
ocr/image_reader.py — Đọc file ảnh (PNG, JPG, ...) thành Document.

Dùng OCR engine để trích xuất chữ từ ảnh.
"""
import os
import base64

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage

from src.app.ocr.engine import extract_text
from src.app.rag.llm_factory import get_vision_llm


class ImageOCRLoader:
    """Trích xuất văn bản từ file ảnh bằng OCR engine hoặc Vision LLM."""

    def __init__(self, file_path: str):
        self.file_path = file_path

    def load(self) -> list[Document]:
        basename = os.path.basename(self.file_path)
        print(f"  👁️  Đang phân tích ảnh/biểu đồ: {basename}")

        vision_llm = get_vision_llm()
        ocr_text = ""

        if vision_llm:
            try:
                print("      🔍 Đang dùng Vision API để đọc hiểu hình ảnh...")
                with open(self.file_path, "rb") as f:
                    img_b64 = base64.b64encode(f.read()).decode("utf-8")
                
                # Xác định MIME type cơ bản
                ext = self.file_path.lower().split('.')[-1]
                mime_type = f"image/{ext}" if ext in ["png", "jpeg", "jpg", "webp", "gif"] else "image/png"
                if mime_type == "image/jpg": mime_type = "image/jpeg"

                msg = HumanMessage(content=[
                    {
                        "type": "text", 
                        "text": "Bạn là một chuyên gia phân tích dữ liệu. Đây là một hình ảnh được trích xuất từ tài liệu báo cáo. Hãy đọc tất cả chữ trong ảnh. Đặc biệt, nếu đây là một BIỂU ĐỒ hoặc ĐỒ THỊ, hãy phân tích chi tiết ý nghĩa, đọc các số liệu quan trọng, và chỉ ra xu hướng (tăng/giảm). Nếu đây chỉ là ảnh minh họa bình thường, hãy miêu tả ngắn gọn."
                    },
                    {
                        "type": "image_url", 
                        "image_url": {"url": f"data:{mime_type};base64,{img_b64}"}
                    }
                ])
                res = vision_llm.invoke([msg])
                ocr_text = res.content
            except Exception as e:
                print(f"      ⚠️ Vision API gặp lỗi: {e}. Fallback về OCR local...")
                ocr_text = extract_text(self.file_path)
        else:
            print("      🔍 Đang nhận dạng chữ bằng OCR local (PaddleOCR)...")
            ocr_text = extract_text(self.file_path)

        content = (
            f"[PHÂN TÍCH ẢNH/BIỂU ĐỒ: {basename}]\n"
            f"{ocr_text}"
        )
        return [Document(
            page_content=content,
            metadata={"source": self.file_path, "page": 1}
        )]
