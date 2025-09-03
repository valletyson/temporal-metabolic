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

# Copy the worker scripts
COPY aws-deploy/docker/worker_simple.py .
COPY aws-deploy/docker/worker_auto_shutdown.py .

# Run the auto-shutdown worker by default
CMD ["python", "worker_auto_shutdown.py"]