FROM python:3.10-slim-bookworm

# Install PostgreSQL client
RUN apt-get update \
 && apt-get install -y curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Setup for SSL certificates
RUN mkdir -p /etc/ssl/custom-certs
# We will use environment variable ROOT_CERT content in entrypoint script

# Copy project files
COPY . .

# Make the entrypoint script executable
RUN chmod +x /app/docker-entrypoint.sh

# Create directories
RUN mkdir -p static media

# Expose port
EXPOSE 8000

# Set the entrypoint
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Default command
CMD ["run", "--host", "0.0.0.0", "--port", "8000"] 