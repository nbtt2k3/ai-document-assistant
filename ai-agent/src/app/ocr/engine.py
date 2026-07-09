"""
ocr/engine.py — OCR Engine singleton + unified interface.

Cung cấp:
- get_ocr_reader() : trả về singleton OCR reader (lazy init)
- extract_text(file_path) : interface chung extract_text → str
"""
import logging
import os

# Tắt tính năng PIR mới của PaddlePaddle 3.x để sửa lỗi ConvertPirAttribute2RuntimeAttribute trên CPU Windows
os.environ["FLAGS_enable_pir_api"] = "0"
os.environ["FLAGS_use_mkldnn"] = "0"

import cv2
from paddleocr import PPStructure
from markdownify import markdownify

# ── Singleton (lazy init) ──────────────
_ocr_reader = None

def get_ocr_reader():
    """Trả về PPStructure singleton. Khởi tạo lần đầu khi được gọi."""
    global _ocr_reader
    if _ocr_reader is None:
        print("[INFO] Đang nạp model PP-Structure lần đầu...")
        try:
            # Tắt cảnh báo log debug của PaddleOCR
            logging.getLogger("ppocr").setLevel(logging.ERROR)
            
            # Khởi tạo PPStructure, dùng image_orientation=True nếu cần xoay ảnh
            _ocr_reader = PPStructure(lang='en', show_log=False, recovery=True)
            print("[INFO] PP-Structure model đã sẵn sàng.")
        except Exception as e:
            print(f"[ERROR] Lỗi khởi tạo OCR: {e}")
            _ocr_reader = None
    return _ocr_reader


def extract_text(file_path: str) -> str:
    """
    Interface chung: trích xuất văn bản & bảng biểu từ file ảnh bằng PP-Structure.
    """
    reader = get_ocr_reader()
    if not reader:
        return ""
    try:
        # PP-Structure yêu cầu truyền vào ảnh OpenCV (numpy array)
        img = cv2.imread(file_path)
        if img is None:
            print(f"      [ERROR] Không thể đọc ảnh bằng cv2: {file_path}")
            return ""
            
        result = reader(img)
        if not result:
            return ""
            
        final_text = []
        for line in result:
            region_type = line.get('type', '')
            res = line.get('res', [])
            
            if region_type == 'table' and isinstance(res, dict) and 'html' in res:
                html_table = res['html']
                md_table = markdownify(html_table).strip()
                final_text.append("\n" + md_table + "\n")
            else:
                # Đối với text, title, figure, res là một list các dict [{'text': ..., 'confidence': ...}]
                if isinstance(res, list):
                    texts = [r.get('text', '') for r in res if isinstance(r, dict) and 'text' in r]
                    if texts:
                        final_text.append(" ".join(texts))
                        
        return "\n".join(final_text).strip()
    except Exception as e:
        print(f"      [ERROR] Lỗi OCR PP-Structure: {e}")
        return f"[Lỗi OCR: {e}]"
