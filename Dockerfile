FROM python:3.10-slim-bookworm

# Install PostgreSQL client
RUN apt-get update \
 && apt-get install -y curl gnupg lsb-release \
 && curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor -o /usr/share/keyrings/postgresql-keyring.gpg \
 && echo "deb [signed-by=/usr/share/keyrings/postgresql-keyring.gpg] http://apt.postgresql.org/pub/repos/apt/ $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list \
 && apt-get update \
 && apt-get install -y postgresql-client-16 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


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