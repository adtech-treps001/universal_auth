# BDD Test Runner with Playwright Dockerfile
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install --with-deps

# Copy test files
COPY . .

# Create test results directory
RUN mkdir -p /app/test_results

# Set environment variables
ENV PYTHONPATH=/app
ENV HEADLESS=true
ENV BASE_URL=http://frontend:3000
ENV API_URL=http://backend:8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import playwright; print('Playwright ready')" || exit 1

# Default command (can be overridden)
CMD ["python", "-m", "pytest", "-v", "--tb=short", "--html=test_results/report.html", "--self-contained-html"]