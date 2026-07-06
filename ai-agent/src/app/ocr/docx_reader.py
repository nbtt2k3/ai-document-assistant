"""
ocr/docx_reader.py — Đọc DOCX thành list[Document].

Trích xuất văn bản chính bằng mammoth (giữ Heading) + OCR ảnh nhúng bằng PaddleOCR.
"""
import os
import glob
import tempfile

from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter
from PIL import Image

from src.app.ocr.image_reader import ImageOCRLoader


class CustomDocxLoader:
    """Đọc DOCX: dùng mammoth lấy Markdown + OCR ảnh nhúng bằng PaddleOCR."""

    def __init__(self, file_path: str):
        self.file_path = file_path

    def load(self) -> list[Document]:
        import docx2txt
        import mammoth
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
