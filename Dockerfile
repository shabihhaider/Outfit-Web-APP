# ============================================================
# Stage 1 — Build React frontend
# ============================================================
FROM node:18-slim AS frontend-build
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
ENV VITE_API_URL=""
RUN npm run build

# ============================================================
# Stage 2 — Python backend + serve built frontend
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

# Built frontend from Stage 1
COPY --from=frontend-build /frontend/dist ./frontend/dist

# Runtime directories
RUN mkdir -p uploads instance && chmod 777 uploads instance
RUN chmod +x entrypoint.sh

# Hugging Face Spaces default port
EXPOSE 7860

# Run migrations + start app
CMD ["./entrypoint.sh"]
