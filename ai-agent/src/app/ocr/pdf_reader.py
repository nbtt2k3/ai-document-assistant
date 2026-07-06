"""
ocr/pdf_reader.py — Đọc PDF thành list[Document].

Trích xuất văn bản chính bằng MarkItDown/PyMuPDF + OCR ảnh nhúng bằng PaddleOCR.
"""
import os
import tempfile

from langchain_core.documents import Document
from PIL import Image
import io

from src.app.ocr.image_reader import ImageOCRLoader


class CustomPDFLoader:
    """Đọc PDF: dùng pymupdf4llm lấy Markdown + OCR ảnh nhúng bằng PaddleOCR."""

    def __init__(self, file_path: str):
        self.file_path = file_path

    def load(self) -> list[Document]:
        import fitz
        
        docs = []
        try:
            # Trích xuất markdown (Sử dụng MarkItDown để lấy nội dung chuẩn)
            try:
                from markitdown import MarkItDown
                md = MarkItDown()
                result = md.convert(self.file_path)
                combined_md = result.text_content
            except Exception as e:
                combined_md = ""
                doc_fitz = fitz.open(self.file_path)
                for page in doc_fitz:
                    combined_md += page.get_text() + "\n\n"
                doc_fitz.close()
                
            doc_fitz = fitz.open(self.file_path)

            img_contents = []
            for page_num in range(len(doc_fitz)):
                page_fitz = doc_fitz[page_num]
                image_list = page_fitz.get_images(full=True)
                
                for img_index, img in enumerate(image_list):
                    xref = img[0]
                    base_image = doc_fitz.extract_image(xref)
                    image_bytes = base_image["image"]
                    
                    try:
                        img_pil = Image.open(io.BytesIO(image_bytes))
                        if img_pil.width < 100 or img_pil.height < 100:
                            continue
                        if img_pil.mode not in ("RGB", "L"):
                            img_pil = img_pil.convert("RGB")
                            
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                            img_pil.save(tmp, format="PNG")
                            tmp_path = tmp.name
                    except Exception as e:
                        continue

                    try:
                        img_docs = ImageOCRLoader(tmp_path).load()
                        if img_docs:
                            img_contents.append(img_docs[0].page_content)
                    finally:
                        os.unlink(tmp_path)
                
            if img_contents:
                combined_md += "\n\n=== NỘI DUNG ẢNH TRONG TÀI LIỆU ===\n" + "\n\n".join(img_contents)

            docs.append(Document(page_content=combined_md, metadata={"source": self.file_path}))

        except Exception as e:
            print(f"  [ERROR] Lỗi đọc PDF: {e}")
        return docs
