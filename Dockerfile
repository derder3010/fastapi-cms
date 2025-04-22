FROM python:3.10-slim-bookworm

# Install curl, build deps, and uv
RUN apt-get update && apt-get install -y curl build-essential libssl-dev libffi-dev \
 && curl -LsSf https://astral.sh/uv/install.sh | sh \
 && mv /root/.cargo/bin/uv /usr/local/bin/uv \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Copy and install dependencies
COPY requirements.txt .
RUN uv pip install -r requirements.txt

# Copy app files
COPY . .

# Set permissions
RUN chmod +x /app/docker-entrypoint.sh
RUN mkdir -p static media

EXPOSE 8000

ENTRYPOINT ["/app/docker-entrypoint.sh"]

CMD ["run", "--host", "0.0.0.0", "--port", "8000"]
