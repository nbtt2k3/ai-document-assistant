"""
ocr/markitdown_reader.py — Universal reader dùng Microsoft MarkItDown.

Đọc nội dung từ Excel (.xlsx), CSV, PPTX thành văn bản Markdown rất tốt.
"""
from langchain_core.documents import Document
from markitdown import MarkItDown

class MarkItDownLoader:
    def __init__(self, file_path: str):
        self.file_path = file_path

    def load(self) -> list[Document]:
        docs = []
        try:
            md = MarkItDown()
            result = md.convert(self.file_path)
            
            # Chúng ta có thể dùng MarkdownHeaderTextSplitter để cắt chunk,
            # Hoặc trả về cục nguyên khối để TextSplitter gốc tự lo.
            if result and result.text_content:
                docs.append(Document(
                    page_content=result.text_content,
                    metadata={"source": self.file_path}
                ))
            else:
                print(f"  [WARNING] MarkItDown không trích xuất được gì từ {self.file_path}")
        except Exception as e:
            print(f"  [ERROR] Lỗi đọc bằng MarkItDown: {e}")
            
        return docs
