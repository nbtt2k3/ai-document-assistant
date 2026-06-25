"""
ocr/engine.py — OCR Engine singleton + unified interface.

Cung cấp:
- get_ocr_reader() : trả về singleton OCR reader (lazy init)
- extract_text(file_path) : interface chung extract_text → str

Hỗ trợ thay engine bằng cách sửa OCR_ENGINE trong config.py.
"""
import easyocr

from src.app.ocr.config import OCR_LANGUAGES, OCR_GPU

# ── Singleton (lazy init, chỉ load model 1 lần khi gọi lần đầu) ──────────────
_ocr_reader = None


def get_ocr_reader():
    """Trả về OCR reader singleton. Khởi tạo lần đầu khi được gọi."""
    global _ocr_reader
    if _ocr_reader is None:
        print("[INFO] Đang nạp model OCR lần đầu...")
        try:
            _ocr_reader = easyocr.Reader(OCR_LANGUAGES, gpu=OCR_GPU, verbose=False)
            print("[INFO] OCR model đã sẵn sàng.")
        except Exception as e:
            print(f"❌ Lỗi khởi tạo OCR: {e}")
            _ocr_reader = None
    return _ocr_reader


def extract_text(file_path: str) -> str:
    """
    Interface chung: trích xuất văn bản từ file ảnh.

    Args:
        file_path: Đường dẫn tuyệt đối đến file ảnh (PNG, JPG, ...).

    Returns:
        Chuỗi văn bản nhận dạng được, hoặc chuỗi rỗng nếu thất bại.
    """
    reader = get_ocr_reader()
    if not reader:
        return ""
    try:
        result = reader.readtext(file_path, detail=0, paragraph=True)
        return " ".join(result) if result else ""
    except Exception as e:
        print(f"      ❌ Lỗi OCR: {e}")
        return f"[Lỗi OCR: {e}]"
