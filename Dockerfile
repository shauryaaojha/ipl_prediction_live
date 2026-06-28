# ============================================
# IPL 2026 Data Scraper — Dockerfile
# ============================================
FROM python:3.12-slim

# System dependencies for lxml, psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libxml2-dev \
    libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

# Working directory
WORKDIR /app

# Copy requirements first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the full project
COPY . .

# Create data directories
RUN mkdir -p /app/data/raw_html /app/data/logs /app/data/exports /app/data/cache

# Environment defaults
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV DATA_PATH=/app/data
ENV DB_HOST=postgres
ENV DB_PORT=5432
ENV DB_NAME=ipl2026
ENV DB_USER=ipl_user
ENV DB_PASSWORD=ipl_secure_2026

# Entry point
ENTRYPOINT ["python", "-m"]
CMD ["src.cli", "--help"]
