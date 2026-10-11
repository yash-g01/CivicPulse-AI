# ============================================================================
# CivicPulse AI - Production Container (FastAPI + Playwright Chromium)
# Suitable for AWS EC2, AWS ECS Fargate, AWS App Runner, or Docker Swarm
# ============================================================================

FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered streaming logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HEADLESS_BROWSER=true \
    PORT=8000

# Install required system packages and Playwright dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright Chromium and required OS browser drivers
RUN playwright install --with-deps chromium

# Create ephemeral directory for evidence staging
RUN mkdir -p /tmp/civicpulse && chmod 777 /tmp/civicpulse

# Copy application source code and test fixtures
COPY app/ ./app/
COPY tests/ ./tests/

# Container Healthcheck for AWS Application Load Balancers / ECS / App Runner
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

# Launch Uvicorn ASGI server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
