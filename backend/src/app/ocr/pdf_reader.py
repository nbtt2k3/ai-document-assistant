"""
ocr/pdf_reader.py — Đọc PDF, DOCX, TXT thành list[Document].

Mỗi loader:
- Trích xuất văn bản chính
- OCR các ảnh nhúng bên trong (dùng ImageOCRLoader)

FILE_LOADERS: registry ánh xạ đuôi file → loader class.
"""
import os
import glob
import tempfile

from langchain_community.document_loaders import TextLoader
from langchain_core.documents import Document
from pypdf import PdfReader
import docx2txt
from PIL import Image
import io

from src.app.ocr.image_reader import ImageOCRLoader


# ── PDF ───────────────────────────────────────────────────────────────────────

class CustomPDFLoader:
    """Đọc PDF: dùng pymupdf4llm lấy Markdown + OCR ảnh nhúng bằng PaddleOCR."""

    def __init__(self, file_path: str):
        self.file_path = file_path

    def load(self) -> list[Document]:
        import pymupdf4llm
        import fitz
        from langchain_text_splitters import MarkdownHeaderTextSplitter
        
        docs = []
        try:
            # 1. Trích xuất markdown (Sử dụng MarkItDown thay vì pymupdf4llm để tránh lỗi ONNX trên Windows)
            try:
                from markitdown import MarkItDown
                md = MarkItDown()
                result = md.convert(self.file_path)
                combined_md = result.text_content
            except Exception as e:
                print(f"  [WARNING] Lỗi MarkItDown: {e}. Fallback sang fitz text thường...")
                combined_md = ""
                temp_doc = fitz.open(self.file_path)
                for page in temp_doc:
                    combined_md += page.get_text() + "\n\n"
                temp_doc.close()
                
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
                        print(f"  [ERROR] Lỗi convert ảnh {img_index+1} sang PNG: {e}")
                        continue

                    try:
                        print(f"  [INFO] Ảnh {img_index+1} — trang {page_num+1} ({os.path.basename(self.file_path)})")
                        img_docs = ImageOCRLoader(tmp_path).load()
                        if img_docs:
                            img_contents.append(img_docs[0].page_content)
                    finally:
                        os.unlink(tmp_path)
                
            if img_contents:
                combined_md += "\n\n=== NỘI DUNG ẢNH TRONG TÀI LIỆU ===\n" + "\n\n".join(img_contents)

            # 2. Cắt văn bản dựa trên Header (Chương/Mục)
            headers_to_split_on = [
                ("#", "Header 1"),
                ("##", "Header 2"),
                ("###", "Header 3"),
            ]
            markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
            md_header_splits = markdown_splitter.split_text(combined_md)
            
            for split in md_header_splits:
                split.metadata["source"] = self.file_path
                docs.append(split)

        except Exception as e:
            print(f"  [ERROR] Lỗi đọc PDF: {e}")
        return docs


# ── DOCX ──────────────────────────────────────────────────────────────────────

class CustomDocxLoader:
    """Đọc DOCX: dùng mammoth lấy Markdown + OCR ảnh nhúng bằng PaddleOCR."""

    def __init__(self, file_path: str):
        self.file_path = file_path

    def load(self) -> list[Document]:
        import docx2txt
        import mammoth
        from langchain_text_splitters import MarkdownHeaderTextSplitter
        docs = []
        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                # Dùng docx2txt chỉ để trích xuất ảnh ra tmp_dir
                _ = docx2txt.process(self.file_path, tmp_dir)

                # Dùng mammoth để lấy văn bản dạng Markdown (giữ được Heading)
                with open(self.file_path, "rb") as docx_file:
                    result = mammoth.convert_to_markdown(docx_file)
                    md_text = result.value

                img_contents = []
                for img_file in glob.glob(os.path.join(tmp_dir, "*")):
                    try:
                        with Image.open(img_file) as img:
                            if img.width < 100 or img.height < 100:
                                print(f"  ⏩ Bỏ qua ảnh DOCX (kích thước quá nhỏ: {img.width}x{img.height})")
                                continue
                    except Exception:
                        pass
                        
                    print(f"  [INFO] Ảnh trong DOCX: {os.path.basename(self.file_path)}")
                    img_docs = ImageOCRLoader(img_file).load()
                    if img_docs:
                        img_contents.append(img_docs[0].page_content)

                combined_md = md_text
                if img_contents:
                    combined_md += "\n\n=== NỘI DUNG ẢNH ===\n" + "\n\n".join(img_contents)

                # Cắt văn bản dựa trên Header
                headers_to_split_on = [
                    ("#", "Header 1"),
                    ("##", "Header 2"),
                    ("###", "Header 3"),
                ]
                markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
                md_header_splits = markdown_splitter.split_text(combined_md)

                for split in md_header_splits:
                    split.metadata["source"] = self.file_path
                    docs.append(split)

        except Exception as e:
            print(f"  [ERROR] Lỗi đọc DOCX: {e}")
        return docs


# ── Registry ──────────────────────────────────────────────────────────────────

# Mapping: đuôi file → loader class
FILE_LOADERS: dict = {
    ".pdf":  CustomPDFLoader,
    ".txt":  TextLoader,
    ".docx": CustomDocxLoader,
}

SUPPORTED_EXTENSIONS = set(FILE_LOADERS.keys())
