FROM --platform=$BUILDPLATFORM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libmagic1 \
    libmagic-dev \
    build-essential \
    tesseract-ocr \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python packages
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir wheel setuptools && \
    pip install --no-cache-dir transliterate==1.10.2 && \
    pip install --no-cache-dir -r requirements.txt

# Install playwright dependencies
RUN playwright install-deps && \
    playwright install chromium

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Start the application with debug logging
CMD ["python", "-m", "gunicorn", "main:app", "--workers", "1", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--timeout", "300", "--log-level", "debug", "--capture-output", "--enable-stdio-inheritance"] 