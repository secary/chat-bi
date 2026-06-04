ARG NODE_IMAGE=node:22-bookworm-slim
ARG PYTHON_IMAGE=python:3.11-slim
FROM ${NODE_IMAGE} AS frontend-deps

WORKDIR /app

ARG NPM_REGISTRY=https://registry.npmjs.org
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --registry=${NPM_REGISTRY} \
    && touch node_modules/.install-stamp

FROM frontend-deps AS frontend-build

COPY frontend ./
COPY docs/help /docs/help
ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build


FROM ${PYTHON_IMAGE} AS backend-base

WORKDIR /app

ARG DEBIAN_MIRROR=http://deb.debian.org/debian
ARG DEBIAN_SECURITY_MIRROR=http://deb.debian.org/debian-security
RUN sed -i \
        -e "s|http://deb.debian.org/debian-security|${DEBIAN_SECURITY_MIRROR}|g" \
        -e "s|http://security.debian.org/debian-security|${DEBIAN_SECURITY_MIRROR}|g" \
        -e "s|http://deb.debian.org/debian|${DEBIAN_MIRROR}|g" \
        -e "s|http://ftp.debian.org/debian|${DEBIAN_MIRROR}|g" \
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
ARG PIP_INDEX_URL=https://pypi.org/simple
ENV UV_INDEX_URL=${PIP_INDEX_URL}
RUN pip install --no-cache-dir --index-url ${PIP_INDEX_URL} uv \
    && uv sync --frozen --no-install-project

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
