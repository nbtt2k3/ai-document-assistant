FROM python:3.10-slim

# Install system dependencies for OCR (paddleocr) and python packages
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
