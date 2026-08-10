FROM python:3.12-slim

# System dependencies:
# - tesseract-ocr: required by pytesseract (app/analysis/detectors/ocr.py)
# - libgl1, libglib2.0-0: required by opencv-python at import time
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
ENV PYTHONPATH=/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY frontend/ ./frontend/
COPY scripts/init_db.py ./scripts/init_db.py

EXPOSE 8000

CMD ["sh", "-c", "python scripts/init_db.py && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
