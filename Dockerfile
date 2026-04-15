# Gunakan image Python slim yang ringan
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install uv (tools untuk manajemen package yang cepat)
RUN pip install uv

# Copy file konfigurasi dependency
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen

# Copy seluruh source code
COPY . .

# Beritahu port yang digunakan
EXPOSE 8000

# Command untuk menjalankan aplikasi
# Pastikan main.py ada di dalam folder app/
CMD ["uv", "run", "fastapi", "run", "app/main.py", "--port", "8000"]