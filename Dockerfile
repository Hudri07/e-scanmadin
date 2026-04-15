# Gunakan image resmi uv yang sudah siap pakai
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

# Copy file konfigurasi dependency saja
COPY pyproject.toml uv.lock ./

# Install dependencies menggunakan uv secara langsung
# Ini menggantikan kebutuhan akan skrip eksternal .sh
RUN uv sync --frozen --no-dev

# Copy seluruh source code
COPY . .

# Jalankan aplikasi (sesuaikan path ke main.py Anda)
CMD ["uv", "run", "fastapi", "run", "app/main.py", "--port", "8000"]