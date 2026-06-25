"""
ocr/config.py — Cấu hình OCR Engine.

Thay đổi engine OCR (easyocr/tesseract/paddle) chỉ cần sửa ở đây,
không cần động vào các file khác.
"""

# Engine sử dụng: "easyocr" (mặc định)
OCR_ENGINE = "easyocr"

# Ngôn ngữ nhận dạng
OCR_LANGUAGES = ['vi', 'en']

# Dùng GPU hay không (False = tương thích mọi máy)
OCR_GPU = False
