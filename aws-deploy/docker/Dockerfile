FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install additional AWS dependencies
RUN pip install --no-cache-dir boto3 cobra

# Copy the temporal-metabolic package
COPY temporal/ ./temporal/
COPY pyproject.toml .
COPY README.md .

# Install the package
RUN pip install -e .

# Copy the worker script
COPY aws-deploy/docker/worker_simple.py .

# Run the worker
CMD ["python", "worker_simple.py"]