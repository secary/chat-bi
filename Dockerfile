ARG NODE_IMAGE=node:22-bookworm-slim
ARG PYTHON_IMAGE=python:3.11-slim
ARG PACKAGE_MIRROR_CN=0
FROM ${NODE_IMAGE} AS frontend-deps

WORKDIR /app

ARG PACKAGE_MIRROR_CN
COPY frontend/package.json frontend/package-lock.json ./
RUN case "${PACKAGE_MIRROR_CN}" in \
        0) npm_registry="https://registry.npmjs.org" ;; \
        1) \
            npm_registry=""; \
            for candidate in \
                "https://registry.npmmirror.com" \
                "https://mirrors.huaweicloud.com/repository/npm/" \
                "https://registry.npmjs.org"; do \
                if npm view vitest@4.1.8 version --registry="${candidate}" >/dev/null 2>&1; then \
                    npm_registry="${candidate}"; \
                    break; \
                fi; \
            done; \
            if [ -z "${npm_registry}" ]; then \
                echo "No reachable npm registry found." >&2; \
                exit 2; \
            fi ;; \
        *) echo "Unsupported PACKAGE_MIRROR_CN=${PACKAGE_MIRROR_CN}. Use 0 or 1." >&2; exit 2 ;; \
    esac \
    && echo "Using npm registry: ${npm_registry}" \
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
            . /etc/os-release; \
            debian_mirror=""; \
            debian_security_mirror=""; \
            for candidate in \
                "https://mirrors.tuna.tsinghua.edu.cn/debian|https://mirrors.tuna.tsinghua.edu.cn/debian-security" \
                "https://mirrors.ustc.edu.cn/debian|https://mirrors.ustc.edu.cn/debian-security" \
                "https://mirrors.huaweicloud.com/debian|https://mirrors.huaweicloud.com/debian-security" \
                "http://deb.debian.org/debian|http://deb.debian.org/debian-security"; do \
                main_mirror="${candidate%%|*}"; \
                security_mirror="${candidate#*|}"; \
                if python -c "import sys, urllib.request; urllib.request.urlopen(sys.argv[1], timeout=8).read(1); urllib.request.urlopen(sys.argv[2], timeout=8).read(1)" \
                    "${main_mirror}/dists/${VERSION_CODENAME}/InRelease" \
                    "${security_mirror}/dists/${VERSION_CODENAME}-security/InRelease" >/dev/null 2>&1; then \
                    debian_mirror="${main_mirror}"; \
                    debian_security_mirror="${security_mirror}"; \
                    break; \
                fi; \
            done; \
            if [ -z "${debian_mirror}" ]; then \
                echo "No reachable Debian mirror found." >&2; \
                exit 2; \
            fi ;; \
        *) echo "Unsupported PACKAGE_MIRROR_CN=${PACKAGE_MIRROR_CN}. Use 0 or 1." >&2; exit 2 ;; \
    esac \
    && echo "Using Debian mirror: ${debian_mirror}" \
    && echo "Using Debian security mirror: ${debian_security_mirror}" \
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
        1) \
            pip_index=""; \
            for candidate in \
                "https://pypi.tuna.tsinghua.edu.cn/simple" \
                "https://mirrors.ustc.edu.cn/pypi/simple" \
                "https://repo.huaweicloud.com/repository/pypi/simple" \
                "https://pypi.org/simple"; do \
                if python -c "import sys, urllib.request; urllib.request.urlopen(sys.argv[1], timeout=8).read(1)" "${candidate}/uv/" >/dev/null 2>&1; then \
                    pip_index="${candidate}"; \
                    break; \
                fi; \
            done; \
            if [ -z "${pip_index}" ]; then \
                echo "No reachable PyPI index found." >&2; \
                exit 2; \
            fi ;; \
        *) echo "Unsupported PACKAGE_MIRROR_CN=${PACKAGE_MIRROR_CN}. Use 0 or 1." >&2; exit 2 ;; \
    esac \
    && echo "Using PyPI index: ${pip_index}" \
    && pip install --no-cache-dir --index-url "${pip_index}" --timeout 120 --retries 5 uv \
    && uv export --frozen --no-dev --no-hashes --no-emit-project --no-header --output-file /tmp/requirements.txt \
    && uv venv .venv --no-progress \
    && UV_DEFAULT_INDEX="${pip_index}" \
        UV_INDEX_URL="${pip_index}" \
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
