FROM python:3.11-slim

# Install system dependencies including Tesseract OCR and English language data
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    libtesseract-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Production build verification: confirm Tesseract binary and language models exist
RUN tesseract --version && tesseract --list-langs

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
