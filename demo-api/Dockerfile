FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev

COPY demo-api/ ./demo-api/

CMD ["uv", "run", "uvicorn", "main:app", "--app-dir", "demo-api", "--host", "0.0.0.0", "--port", "8000"]
