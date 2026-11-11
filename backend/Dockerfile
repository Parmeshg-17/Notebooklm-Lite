FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies needed for PyMuPDF, build tools, and curl for health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libmupdf-dev \
    && rm -rf /var/lib/apt/lists/*

# Create dedicated non-root user (UID 10001) for container security hardening
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/bash -m appuser

# Copy and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend application source code
COPY . .

# Create uploads directory and establish ownership for non-root execution
RUN mkdir -p /app/uploads && \
    chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

EXPOSE 8000

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Container healthcheck for AWS ECS Fargate and container orchestrators
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Production ASGI server configuration with graceful SIGTERM termination
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--timeout-keep-alive", "65", "--timeout-graceful-shutdown", "30"]
