"""
ocr/excel_reader.py — Đọc file Excel (.xlsx) thành list[Document].

Dùng pandas để duyệt qua từng Sheet, chia nhỏ bảng tính thành các bảng Markdown
để LLM dễ đọc và không bị ngợp (vượt context).
"""
import os
import pandas as pd
from langchain_core.documents import Document

CHUNK_ROWS = 50  # Số dòng tối đa mỗi bảng để LLM không bị ngợp

class CustomExcelLoader:
    def __init__(self, file_path: str):
        self.file_path = file_path

    def load(self) -> list[Document]:
        docs = []
        basename = os.path.basename(self.file_path)
        print(f"  📊 Đang đọc file Excel: {basename}")
        
        try:
            excel_file = pd.ExcelFile(self.file_path)
            
            for sheet_name in excel_file.sheet_names:
                print(f"      - Đang xử lý Sheet: '{sheet_name}'")
                
                # Đọc toàn bộ sheet thành DataFrame, bỏ qua các dòng/cột rỗng hoàn toàn
                df = pd.read_excel(excel_file, sheet_name=sheet_name)
                df = df.dropna(how='all').dropna(axis=1, how='all')
                
                if df.empty:
                    continue
                
                total_rows = len(df)
                
                # Chia nhỏ dataframe nếu quá lớn
                for i in range(0, total_rows, CHUNK_ROWS):
                    chunk_df = df.iloc[i:i + CHUNK_ROWS]
                    
                    # Chuyển DataFrame thành Markdown table
                    md_table = chunk_df.to_markdown(index=False)
                    
                    content = (
                        f"=== BẢNG TÍNH EXCEL ===\n"
                        f"- File: {basename}\n"
                        f"- Sheet: {sheet_name}\n"
                        f"- Phần: {i // CHUNK_ROWS + 1} / {(total_rows - 1) // CHUNK_ROWS + 1}\n\n"
                        f"{md_table}"
                    )
                    
                    docs.append(Document(
                        page_content=content,
                        metadata={
                            "source": self.file_path, 
                            "sheet": sheet_name,
                            "page": (i // CHUNK_ROWS) + 1  # Dùng page để tương thích với hệ thống gốc
                        }
                    ))
                    
        except Exception as e:
            print(f"  [ERROR] Lỗi đọc file Excel {basename}: {e}")
            
        return docs
