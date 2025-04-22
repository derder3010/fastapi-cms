FROM python:3.10-slim-bookworm

# Install curl and dependencies for uv
RUN apt-get update && apt-get install -y curl gcc libffi-dev libssl-dev \
 && curl -LsSf https://astral.sh/uv/install.sh | sh \
 && rm -rf /var/lib/apt/lists/*

# Add uv to PATH (nếu cài theo mặc định)
ENV PATH="/root/.cargo/bin:$PATH"

WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Copy requirements
COPY requirements.txt .

# Install dependencies using uv (fast)
RUN uv pip install -r requirements.txt

# Copy the entire app
COPY . .

# Make entrypoint executable
RUN chmod +x /app/docker-entrypoint.sh

# Create folders
RUN mkdir -p static media

EXPOSE 8000

ENTRYPOINT ["/app/docker-entrypoint.sh"]

CMD ["run", "--host", "0.0.0.0", "--port", "8000"]
