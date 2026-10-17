# Imagen de la API + MCP (Railway). Se construye desde la raíz del repo porque la app lee
# data/ (sources.yaml, pricing.yaml, audiences/). Sin torch: los embeddings solo se calculan
# en el job `analyze`, fuera de esta imagen (CLAUDE.md §7).
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.18 /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PATH="/app/backend/.venv/bin:$PATH"

WORKDIR /app/backend

COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-default-groups --no-install-project

COPY backend/ ./
COPY data/ /app/data/

# Una sola réplica: migrar al arrancar es seguro y evita un paso manual en cada deploy.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
