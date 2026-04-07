# ============================================================
# OutfitAI — API-only backend (frontend served by Vercel)
# ============================================================
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_CONFIG=production

WORKDIR /app

# System dependencies for OpenCV / Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY app/ app/
COPY engine/ engine/
COPY models/ models/
COPY migrations/ migrations/
COPY run.py .
COPY entrypoint.sh .

# Runtime directories
RUN mkdir -p uploads instance && chmod 777 uploads instance
RUN chmod +x entrypoint.sh

# Hugging Face Spaces default port
EXPOSE 7860

# Run migrations + start app
CMD ["./entrypoint.sh"]
