"""
ocr/pdf_reader.py — Đọc PDF thành list[Document].

Trích xuất văn bản chính bằng MarkItDown/PyMuPDF + OCR ảnh nhúng bằng PaddleOCR.
"""
import os
import io
import tempfile

from langchain_core.documents import Document
from PIL import Image

from src.app.ocr.image_reader import ImageOCRLoader


class CustomPDFLoader:
    """Đọc PDF: dùng pymupdf4llm lấy Markdown + OCR ảnh nhúng bằng PaddleOCR."""

    def __init__(self, file_path: str):
        self.file_path = file_path

    def load(self) -> list[Document]:
        import fitz
        import pymupdf4llm

        docs = []
        try:
            # 1. Trích xuất markdown (per-page)
            try:
                page_chunks = pymupdf4llm.to_markdown(self.file_path, page_chunks=True)
                for chunk in page_chunks:
                    # page metadata của pymupdf4llm là 1-based
                    page_num = chunk.get("metadata", {}).get("page", 0)
                    text = chunk.get("text", "")
                    if text.strip():
                        docs.append(Document(
                            page_content=text,
                            metadata={"source": self.file_path, "page": page_num}
                        ))
            except Exception as e:
                print(f"  [ERROR] Lỗi dùng pymupdf4llm: {e}")
                # Fallback: dùng PyMuPDF trực tiếp
                with fitz.open(self.file_path) as doc_fallback:
                    for i, page in enumerate(doc_fallback):
                        text = page.get_text()
                        if text.strip():
                            docs.append(Document(
                                page_content=text,
                                metadata={"source": self.file_path, "page": i + 1}
                            ))

            # 2. Xử lý ảnh nhúng (OCR) và nối vào trang tương ứng
            with fitz.open(self.file_path) as doc_fitz:
                for page_num in range(len(doc_fitz)):
                    page_fitz = doc_fitz[page_num]
                    image_list = page_fitz.get_images(full=True)
                    
                    img_contents = []
                    for img in image_list:
                        xref = img[0]
                        base_image = doc_fitz.extract_image(xref)
                        image_bytes = base_image["image"]

                        tmp_path = None
                        try:
                            img_pil = Image.open(io.BytesIO(image_bytes))
                            # Bỏ qua ảnh quá nhỏ (icon, logo, v.v.)
                            if img_pil.width < 100 or img_pil.height < 100:
                                continue
                            if img_pil.mode not in ("RGB", "L"):
                                img_pil = img_pil.convert("RGB")

                            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                                img_pil.save(tmp, format="PNG")
                                tmp_path = tmp.name

                            img_docs = ImageOCRLoader(tmp_path).load()
                            if img_docs:
                                img_contents.append(img_docs[0].page_content)

                        except Exception:
                            continue
                        finally:
                            if tmp_path and os.path.exists(tmp_path):
                                os.unlink(tmp_path)
                    
                    if img_contents:
                        img_text = "\n\n=== NỘI DUNG ẢNH TRONG TÀI LIỆU ===\n" + "\n\n".join(img_contents)
                        target_page = page_num + 1
                        
                        # Tìm chunk của trang hiện tại để nối vào
                        doc_found = False
                        for doc in docs:
                            if doc.metadata.get("page") == target_page:
                                doc.page_content += img_text
                                doc_found = True
                                break
                                
                        if not doc_found:
                            docs.append(Document(
                                page_content=img_text,
                                metadata={"source": self.file_path, "page": target_page}
                            ))

        except Exception as e:
            print(f"  [ERROR] Lỗi đọc PDF: {e}")

        return docs
