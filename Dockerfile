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

# Python dependencies — install in two stages to control image size
# Stage 1: lightweight deps first
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip cache purge 2>/dev/null || true \
    && rm -rf /root/.cache/pip /tmp/*

# Application code
COPY app/ app/
COPY engine/ engine/
COPY models/ models/
COPY migrations/ migrations/
COPY run.py .
COPY entrypoint.sh .

# Non-root app user — UID 1000 matches HF Spaces runtime expectation
RUN groupadd -r appuser && useradd -r -g appuser -u 1000 appuser

# Runtime directories — owned by app user, no world-write
RUN mkdir -p uploads instance \
    && chown -R appuser:appuser uploads instance \
    && chmod 755 uploads instance \
    && chmod +x entrypoint.sh

USER appuser

# Hugging Face Spaces default port
EXPOSE 7860

# Run migrations + start app
CMD ["./entrypoint.sh"]
