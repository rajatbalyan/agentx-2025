# Use Python 3.9 as base image
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    chromium \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Install audit tools
RUN npm install -g \
    htmlhint \
    lighthouse \
    hint

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browser
RUN playwright install chromium

# Copy application code
COPY agentx/ agentx/

# Create necessary directories
RUN mkdir -p data/memory/vectors \
    data/memory/conversations \
    logs \
    temp

# Set environment variables
ENV PYTHONPATH=/app
ENV PLAYWRIGHT_BROWSERS_PATH=/app/browser

# Run the application
CMD ["python", "-m", "agentx.system"] 