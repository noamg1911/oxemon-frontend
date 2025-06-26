# Use an official Python 3.8 slim image
FROM python:3.8-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install Python dependencies
RUN pip install --no-cache-dir \
    pyyaml \
    prometheus_client \
    hydration

# Copy your Python code into the container
COPY . /app

# Default command to run your app
CMD ["python", "main.py"]
