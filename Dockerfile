# 빌드 단계
FROM python:3.12-slim-bookworm AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# 의존성 설치
COPY pyproject.toml uv.lock ./
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*
RUN uv sync --frozen --no-cache

# 실행 단계
FROM python:3.12-slim-bookworm

WORKDIR /app

# 가상 환경 복사
COPY --from=builder /app/.venv /app/.venv

# 애플리케이션 코드 복사
COPY . .

# 환경 변수 설정
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"

# 애플리케이션 실행
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
