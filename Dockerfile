ARG NODE_IMAGE=node:22-bookworm-slim
ARG PYTHON_IMAGE=python:3.11-slim
FROM ${NODE_IMAGE} AS frontend-deps

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci \
        --registry=https://registry.npmmirror.com \
        --replace-registry-host=always \
    && touch node_modules/.install-stamp

FROM frontend-deps AS frontend-build

COPY frontend ./
COPY docs/help /docs/help
ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build


FROM ${PYTHON_IMAGE} AS backend-base

WORKDIR /app

RUN sed -i \
        -e "s|http://deb.debian.org/debian-security|https://mirrors.tuna.tsinghua.edu.cn/debian-security|g" \
        -e "s|http://security.debian.org/debian-security|https://mirrors.tuna.tsinghua.edu.cn/debian-security|g" \
        -e "s|http://deb.debian.org/debian|https://mirrors.tuna.tsinghua.edu.cn/debian|g" \
        -e "s|http://ftp.debian.org/debian|https://mirrors.tuna.tsinghua.edu.cn/debian|g" \
        /etc/apt/sources.list /etc/apt/sources.list.d/*.sources 2>/dev/null || true \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        default-mysql-client \
        libcairo2 \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libgdk-pixbuf-2.0-0 \
        libffi-dev \
        nginx \
        shared-mime-info \
        fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock /app/
RUN pip install --no-cache-dir --index-url https://pypi.tuna.tsinghua.edu.cn/simple --timeout 120 --retries 5 uv \
    && uv export --frozen --no-dev --no-hashes --no-emit-project --no-header --output-file /tmp/requirements.txt \
    && uv venv .venv --no-progress \
    && UV_DEFAULT_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple \
        UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
        UV_HTTP_TIMEOUT=120 \
        UV_HTTP_RETRIES=5 \
        UV_CONCURRENT_DOWNLOADS=4 \
        UV_CONCURRENT_BUILDS=2 \
        UV_CONCURRENT_INSTALLS=4 \
        uv pip install --python .venv/bin/python --requirements /tmp/requirements.txt --no-progress

FROM backend-base AS dev

COPY --from=frontend-deps /usr/local /usr/local
COPY --from=frontend-deps /app/node_modules /app/frontend/node_modules
COPY backend /app/backend
COPY skills /app/skills
COPY frontend /app/frontend
COPY docs/help /app/docs/help
COPY deploy/docker-entrypoint.dev.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

EXPOSE 5173 8000

ENTRYPOINT ["/entrypoint.sh"]

FROM backend-base

COPY backend /app/backend
COPY skills /app/skills
COPY deploy/nginx.app.conf /etc/nginx/conf.d/default.conf
RUN rm -f /etc/nginx/sites-enabled/default
COPY deploy/docker-entrypoint.prod.sh /entrypoint.sh
COPY --from=frontend-build /app/dist /usr/share/nginx/html

RUN chmod +x /entrypoint.sh

EXPOSE 80

ENTRYPOINT ["/entrypoint.sh"]
