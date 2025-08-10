# Use official Python runtime as base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8086

# Set default environment variables
ENV PORT=8086
ENV PYTHONUNBUFFERED=1

# Run the application
CMD ["python", "server.py"]