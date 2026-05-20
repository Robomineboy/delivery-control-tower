FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . .

# Build FAISS index on container start if not present
RUN python -c "import os; os.makedirs('data', exist_ok=True)"

EXPOSE 7860

CMD ["python", "api.py"]