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

from src.app.ocr.image_reader import ImageOCRLoader


# ── PDF ───────────────────────────────────────────────────────────────────────

class CustomPDFLoader:
    """Đọc PDF: văn bản từng trang + OCR ảnh nhúng."""

    def __init__(self, file_path: str):
        self.file_path = file_path

    def load(self) -> list[Document]:
        docs = []
        try:
            pdf_doc = PdfReader(self.file_path)
            for page_num, page in enumerate(pdf_doc.pages):
                page_text = page.extract_text() or ""

                img_contents = []
                for img_index, image_obj in enumerate(page.images):
                    image_bytes = image_obj.data
                    ext = image_obj.name.split('.')[-1] if '.' in image_obj.name else "png"

                    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
                        tmp.write(image_bytes)
                        tmp_path = tmp.name

                    try:
                        print(f"  📎 Ảnh {img_index+1} — trang {page_num+1} "
                              f"({os.path.basename(self.file_path)})")
                        img_docs = ImageOCRLoader(tmp_path).load()
                        if img_docs:
                            img_contents.append(img_docs[0].page_content)
                    finally:
                        os.unlink(tmp_path)

                combined = page_text
                if img_contents:
                    combined += "\n\n=== NỘI DUNG ẢNH TRONG TRANG ===\n" + "\n\n".join(img_contents)

                docs.append(Document(
                    page_content=combined,
                    metadata={"source": self.file_path, "page": page_num + 1}
                ))
        except Exception as e:
            print(f"  ❌ Lỗi đọc PDF: {e}")
        return docs


# ── DOCX ──────────────────────────────────────────────────────────────────────

class CustomDocxLoader:
    """Đọc DOCX: văn bản + OCR ảnh nhúng."""

    def __init__(self, file_path: str):
        self.file_path = file_path

    def load(self) -> list[Document]:
        docs = []
        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                text = docx2txt.process(self.file_path, tmp_dir)

                img_contents = []
                for img_file in glob.glob(os.path.join(tmp_dir, "*")):
                    print(f"  📎 Ảnh trong DOCX: {os.path.basename(self.file_path)}")
                    img_docs = ImageOCRLoader(img_file).load()
                    if img_docs:
                        img_contents.append(img_docs[0].page_content)

                combined = text
                if img_contents:
                    combined += "\n\n=== NỘI DUNG ẢNH ===\n" + "\n\n".join(img_contents)

                docs.append(Document(
                    page_content=combined,
                    metadata={"source": self.file_path}
                ))
        except Exception as e:
            print(f"  ❌ Lỗi đọc DOCX: {e}")
        return docs


# ── Registry ──────────────────────────────────────────────────────────────────

# Mapping: đuôi file → loader class
FILE_LOADERS: dict = {
    ".pdf":  CustomPDFLoader,
    ".txt":  TextLoader,
    ".docx": CustomDocxLoader,
}

SUPPORTED_EXTENSIONS = set(FILE_LOADERS.keys())
