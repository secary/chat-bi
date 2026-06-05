ARG NODE_IMAGE=node:22-bookworm-slim
ARG PYTHON_IMAGE=python:3.11-slim
ARG PACKAGE_MIRROR_CN=0
FROM ${NODE_IMAGE} AS frontend-deps

WORKDIR /app

ARG PACKAGE_MIRROR_CN
COPY frontend/package.json frontend/package-lock.json ./
RUN case "${PACKAGE_MIRROR_CN}" in \
        0) npm_registry="https://registry.npmjs.org" ;; \
        1) npm_registry="https://mirrors.tuna.tsinghua.edu.cn/npm/" ;; \
        *) echo "Unsupported PACKAGE_MIRROR_CN=${PACKAGE_MIRROR_CN}. Use 0 or 1." >&2; exit 2 ;; \
    esac \
    && npm ci --registry="${npm_registry}" \
    && touch node_modules/.install-stamp

FROM frontend-deps AS frontend-build

COPY frontend ./
COPY docs/help /docs/help
ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build


FROM ${PYTHON_IMAGE} AS backend-base

WORKDIR /app

ARG PACKAGE_MIRROR_CN
RUN case "${PACKAGE_MIRROR_CN}" in \
        0) \
            debian_mirror="http://deb.debian.org/debian"; \
            debian_security_mirror="http://deb.debian.org/debian-security" ;; \
        1) \
            debian_mirror="https://mirrors.tuna.tsinghua.edu.cn/debian"; \
            debian_security_mirror="https://mirrors.tuna.tsinghua.edu.cn/debian-security" ;; \
        *) echo "Unsupported PACKAGE_MIRROR_CN=${PACKAGE_MIRROR_CN}. Use 0 or 1." >&2; exit 2 ;; \
    esac \
    && sed -i \
        -e "s|http://deb.debian.org/debian-security|${debian_security_mirror}|g" \
        -e "s|http://security.debian.org/debian-security|${debian_security_mirror}|g" \
        -e "s|http://deb.debian.org/debian|${debian_mirror}|g" \
        -e "s|http://ftp.debian.org/debian|${debian_mirror}|g" \
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
ARG PACKAGE_MIRROR_CN
RUN case "${PACKAGE_MIRROR_CN}" in \
        0) pip_index="https://pypi.org/simple" ;; \
        1) pip_index="https://pypi.tuna.tsinghua.edu.cn/simple" ;; \
        *) echo "Unsupported PACKAGE_MIRROR_CN=${PACKAGE_MIRROR_CN}. Use 0 or 1." >&2; exit 2 ;; \
    esac \
    && pip install --no-cache-dir --index-url "${pip_index}" uv \
    && UV_DEFAULT_INDEX="${pip_index}" UV_INDEX_URL="${pip_index}" uv sync --frozen --no-install-project

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
