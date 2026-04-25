# ============================================================
# OutfitAI — API-only backend (frontend served by Vercel)
# Multi-stage build: builder installs deps, runtime is clean.
# ============================================================

# ── Stage 1: builder ─────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Install Python packages into a prefix so we can COPY them cleanly
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: runtime ─────────────────────────────────────────
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_CONFIG=production
# Point Python at the packages installed in the builder stage
ENV PYTHONPATH=/install/lib/python3.11/site-packages
ENV PATH=/install/bin:$PATH

WORKDIR /app

# Runtime system libraries for OpenCV / Pillow (needed at runtime, not just build)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder — no pip, no cache, no build tools
COPY --from=builder /install /install

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
