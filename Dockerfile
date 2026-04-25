FROM python:3.11-slim

# Use a neutral workdir so the Python package `app/` is at /workspace/app, not
# /app/app (some hosts mis-resolve imports when the container root is also /app).
WORKDIR /workspace

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /workspace

# Ensure imports like `from app import env` resolve to /workspace/app
ENV PYTHONPATH=/workspace

# HuggingFace Spaces uses port 7860
EXPOSE 7860

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:7860/health || exit 1

# Start the server
CMD ["uvicorn", "asgi:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]