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

from paddleocr import PaddleOCR

# ── Singleton (lazy init) ──────────────
_ocr_reader = None

def get_ocr_reader():
    """Trả về OCR reader singleton (PaddleOCR). Khởi tạo lần đầu khi được gọi."""
    global _ocr_reader
    if _ocr_reader is None:
        print("[INFO] Đang nạp model PaddleOCR lần đầu...")
        try:
            # Tắt cảnh báo log debug của PaddleOCR
            logging.getLogger("ppocr").setLevel(logging.ERROR)
            
            # Sử dụng ngôn ngữ 'vi' cho tiếng Việt (lưu ý PaddleOCR v3.7.0 bỏ use_gpu, tự detect)
            _ocr_reader = PaddleOCR(use_textline_orientation=True, lang='vi', enable_mkldnn=False)
            print("[INFO] PaddleOCR model đã sẵn sàng.")
        except Exception as e:
            print(f"[ERROR] Lỗi khởi tạo OCR: {e}")
            _ocr_reader = None
    return _ocr_reader


def extract_text(file_path: str) -> str:
    """
    Interface chung: trích xuất văn bản từ file ảnh bằng PaddleOCR.
    """
    reader = get_ocr_reader()
    if not reader:
        return ""
    try:
        # reader.ocr trả về list các trang. Với ảnh thường là 1 list chứa 1 item (page 0)
        # Mỗi item là list các line: [[[box_points], (text, confidence)], ...]
        result = reader.ocr(file_path)
        if not result or not result[0]:
            return ""
            
        text_lines = []
        for line in result[0]:
            # line[1][0] là chuỗi text nhận diện được
            text_lines.append(line[1][0])
            
        return " ".join(text_lines)
    except Exception as e:
        print(f"      [ERROR] Lỗi OCR: {e}")
        return f"[Lỗi OCR: {e}]"
