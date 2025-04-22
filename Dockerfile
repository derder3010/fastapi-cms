# Sử dụng base image của uv
FROM ghcr.io/astral-sh/uv:bookworm-slim AS builder

# Cài đặt curl và các dependencies cần thiết
RUN apt-get update \
 && apt-get install -y curl \
 && rm -rf /var/lib/apt/lists/*

# Cấu hình Python và cài đặt dependencies
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Copy toàn bộ dự án vào container
COPY . /app

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

# Tạo các thư mục cần thiết
RUN mkdir -p static media

# Tạo entrypoint script executable
RUN chmod +x /app/docker-entrypoint.sh

# Expose port 8000
EXPOSE 8000

# Đặt entrypoint
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Lệnh mặc định để chạy ứng dụng FastAPI
CMD ["fastapi", "dev", "--host", "0.0.0.0", "app/main.py"]
