FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy project metadata + source for proper install
COPY pyproject.toml uv.lock* ./
COPY app ./app
COPY tests ./tests

# Install everything including project
RUN uv sync --frozen || uv sync

ENV PYTHONPATH=/app
ENV PATH="/app/.venv/bin:$PATH"

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
