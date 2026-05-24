FROM python:3.11-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        default-mysql-client \
        libcairo2 \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libgdk-pixbuf-2.0-0 \
        libffi-dev \
        shared-mime-info \
        fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock /app/
ARG PIP_INDEX_URL=https://pypi.org/simple
ENV UV_INDEX_URL=${PIP_INDEX_URL}
RUN pip install --no-cache-dir --index-url ${PIP_INDEX_URL} uv \
    && uv sync --frozen --no-install-project

COPY backend /app/backend
COPY skills /app/skills

EXPOSE 8000

CMD [".venv/bin/uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
