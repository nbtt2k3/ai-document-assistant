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
        docs = []
        import fitz
        from src.app.config import LLAMA_CLOUD_API_KEY
        
        # Hàm hỗ trợ để đếm số trang
        def get_total_pages(path: str) -> int:
            with fitz.open(path) as d:
                return len(d)
                
        total_pages = get_total_pages(self.file_path)
        parsed_successfully = False

        # 1. THỬ LLAMAPARSE (NẾU CÓ KEY)
        if LLAMA_CLOUD_API_KEY:
            try:
                print("  [INFO] Dùng LlamaParse để xử lý bố cục phức tạp...")
                import nest_asyncio
                nest_asyncio.apply()
                from llama_parse import LlamaParse
                
                parser = LlamaParse(
                    api_key=LLAMA_CLOUD_API_KEY,
                    result_type="markdown"
                )
                llama_docs = parser.load_data(self.file_path)
                for i, d in enumerate(llama_docs):
                    docs.append(Document(
                        page_content=d.text,
                        metadata={"source": self.file_path, "page": i + 1}
                    ))
                parsed_successfully = True
            except Exception as e:
                print(f"  [WARNING] LlamaParse thất bại (hết hạn mức hoặc lỗi mạng): {e}. Tự động chuyển sang Local...")

        # 2. THỬ PYMUPDF4LLM LOCAL KÈM BATCHING (NẾU LLAMAPARSE THẤT BẠI HOẶC KHÔNG CÓ KEY)
        if not parsed_successfully:
            try:
                print(f"  [INFO] Dùng pymupdf4llm đọc Local theo từng lô 5 trang (Tổng {total_pages} trang)...")
                import pymupdf4llm
                import gc
                
                BATCH_SIZE = 5
                for start_idx in range(0, total_pages, BATCH_SIZE):
                    end_idx = min(start_idx + BATCH_SIZE, total_pages)
                    pages_to_extract = list(range(start_idx, end_idx))
                    
                    # Dùng doc object để tránh lỗi đường dẫn khi chạy batch
                    doc_for_batch = fitz.open(self.file_path)
                    page_chunks = pymupdf4llm.to_markdown(doc_for_batch, pages=pages_to_extract, page_chunks=True)
                    doc_for_batch.close()
                    
                    for chunk in page_chunks:
                        # metadata page của pymupdf4llm là 1-based (tuỳ phiên bản, nhưng ta có thể tin tưởng nó)
                        page_num = chunk.get("metadata", {}).get("page", 0)
                        text = chunk.get("text", "")
                        if text.strip():
                            docs.append(Document(
                                page_content=text,
                                metadata={"source": self.file_path, "page": page_num}
                            ))
                            
                    # Giải phóng bộ nhớ khẩn cấp sau mỗi lô
                    del page_chunks
                    gc.collect()
                    
                # Nếu chạy xong mà không có chữ nào (hoặc quá ít), có thể là file scan
                if not docs or sum(len(d.page_content) for d in docs) < 100:
                    print("  [WARNING] pymupdf4llm không tìm thấy text (có thể là file scan). Chuyển sang OCR...")
                    parsed_successfully = False
                    docs.clear()
                else:
                    parsed_successfully = True
            except Exception as e:
                print(f"  [WARNING] Lỗi dùng pymupdf4llm: {e}. Tự động chuyển sang PyMuPDF thô...")

        # 3. FALLBACK CUỐI CÙNG: ĐỌC TEXT THUẦN BẰNG PYMUPDF
        if not parsed_successfully:
            try:
                print("  [INFO] Dùng PyMuPDF đọc text thuần...")
                with fitz.open(self.file_path) as doc_fallback:
                    for i, page in enumerate(doc_fallback):
                        text = page.get_text()
                        if text.strip():
                            docs.append(Document(
                                page_content=text,
                                metadata={"source": self.file_path, "page": i + 1}
                            ))
            except Exception as e:
                print(f"  [ERROR] Lỗi nghiêm trọng khi đọc PDF bằng mọi cách: {e}")

            # 4. Xử lý ảnh nhúng (OCR) và nối vào trang tương ứng
            print("  [INFO] Đang quét tìm và OCR ảnh trong PDF...")
            import gc
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
                                
                            del img_docs
                        except Exception:
                            continue
                        finally:
                            if tmp_path and os.path.exists(tmp_path):
                                os.unlink(tmp_path)
                            gc.collect()
                    
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



        return docs
