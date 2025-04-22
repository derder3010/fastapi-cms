# Sử dụng base image của uv
FROM ghcr.io/astral-sh/uv:bookworm-slim AS builder

# Cấu hình Python và cài đặt dependencies
WORKDIR /app

# Copy pyproject.toml và uv.lock vào container
COPY pyproject.toml uv.lock ./

# Cài đặt dependencies bằng uv
RUN uv sync --frozen --no-dev

# Copy toàn bộ dự án vào container
COPY . /app

# Tạo các thư mục cần thiết
RUN mkdir -p static media

# Tạo entrypoint script executable
RUN chmod +x /app/docker-entrypoint.sh

# Expose port 8000
EXPOSE 8000

# Đặt entrypoint
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Lệnh mặc định để chạy ứng dụng FastAPI
CMD ["fastapi", "run", "--host", "0.0.0.0", "/app/main.py"]
