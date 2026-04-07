FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:/root/.local/bin:$PATH"

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl postgresql-client \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh

COPY pyproject.toml README.md ./
RUN uv sync --no-dev

COPY . .

# Keep entrypoint outside /app so bind mounts on /app do not override it.
COPY entrypoint.sh /usr/local/bin/backend-entrypoint.sh
RUN chmod 755 /usr/local/bin/backend-entrypoint.sh

CMD ["/usr/local/bin/backend-entrypoint.sh"]
