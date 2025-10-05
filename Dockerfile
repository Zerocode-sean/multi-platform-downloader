# Multi Platform Downloader Dockerfile
# Lightweight production image with non-root user.

FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

WORKDIR /app

# System deps (ffmpeg for yt-dlp muxing). If you want smaller image you can remove ffmpeg.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies first (layer cache)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Allow overriding PORT at runtime: docker run -e PORT=9000 -p 9000:9000 image
CMD ["sh","-c","uvicorn web_app:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers"]
