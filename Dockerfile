FROM python:3.12-slim

WORKDIR /app

# Install system dependencies including ffmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies using fallback paths if needed
COPY requirements.txt* docker/requirements.txt* ./
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; \
    elif [ -f docker/requirements.txt ]; then pip install --no-cache-dir -r docker/requirements.txt; \
    fi

# Copy project files
COPY . ./

# Expose default port
EXPOSE 8000

# Start application using dynamic PORT env var provided by Render (defaulting to 8000)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
