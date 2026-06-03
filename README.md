# 零眸智能 ChatBI

银行场景的对话式数据分析 Demo。生产式运行使用默认 `docker-compose.yml`：MySQL 8.0 容器 + 一体应用容器（nginx + FastAPI + 前端静态资源）。

## 通过 Docker 直接部署

### 1. 准备 `.env`

```bash
cp .env.example .env
```

### 2. 确认必要配置

```dotenv
OPENAI_API_KEY=你的模型Key
LLM_MODEL=openai/你的模型名
API_BASE=https://你的模型服务地址
CHATBI_JWT_SECRET=请替换为强随机密钥
CHATBI_SEED_USERS=admin:强密码:admin
```

### 3. 可选：配置国内源

如果服务器访问 Docker Hub 或海外包源不稳定，可在 `.env` 里使用国内源：

```dotenv
MYSQL_IMAGE=m.daocloud.io/docker.io/library/mysql:8.0
PYTHON_IMAGE=m.daocloud.io/docker.io/library/python:3.11-slim
NODE_IMAGE=m.daocloud.io/docker.io/library/node:22-bookworm-slim
DEBIAN_MIRROR=https://mirrors.tuna.tsinghua.edu.cn/debian
DEBIAN_SECURITY_MIRROR=https://mirrors.tuna.tsinghua.edu.cn/debian-security
PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
NPM_REGISTRY=https://registry.npmmirror.com
```

### 4. 启动服务

```bash
bash scripts/launch.sh --no-open
```

### 5. 访问服务

- 应用：`http://服务器地址:5173`
- MySQL：`服务器地址:3307`

### 6. 常用操作

```bash
docker compose ps
docker compose logs -f
docker compose down
bash scripts/launch.sh --no-build --no-open
```

## CD 示例

仓库已提供 `.github/workflows/deploy-prod.yml`，会在 `ChatBI CI` 的 `main` 分支任务成功后部署，也支持手动 `workflow_dispatch`。

GitHub Environment 名称：

```text
chatbi-prod
```

在 `Settings -> Environments -> chatbi-prod -> Environment secrets` 配置：

| Secret | 示例 |
|---|---|
| `PROD_SSH_HOST` | 你的服务器 IP |
| `PROD_SSH_USER` | `ubuntu` / `root` / `deploy` |
| `PROD_SSH_KEY` | 可登录服务器的 SSH 私钥完整内容 |
| `PROD_DEPLOY_PATH` | `/opt/chat-bi` |
| `PROD_ENV_FILE` | 可选，完整生产 `.env` 内容 |
| `PROD_SSH_PORT` | 可选，默认 `22` |
| `PROD_APP_URL` | 可选，默认 `http://localhost:5173` |
| `TAILSCALE_AUTHKEY` | 可选，仅服务器只在 Tailscale 内网可达时配置 |

如果服务器使用公网 IP 或普通内网 IP，直接填写 `PROD_SSH_HOST=你的服务器 IP` 即可。只有服务器只暴露在 Tailscale 内网时，才需要额外配置 `TAILSCALE_AUTHKEY`，并将 `PROD_SSH_HOST` 填为对应的 Tailscale IP 或 MagicDNS。

一次手动发布：

1. GitHub -> Actions -> `ChatBI Production CD`
2. 点击 `Run workflow`
3. `Git ref to deploy` 填 `main`
4. 首次部署不要勾选 `Reuse existing Docker images on the server`
5. 如果 `chatbi-prod` 开了 required reviewers，批准后开始部署

CD 流程：

```text
preflight: bash -n scripts/launch.sh + docker compose config + launch 单测
-> 可选 Tailscale 接入
-> SSH/rsync 同步代码
-> 写入可选 PROD_ENV_FILE
-> bash scripts/launch.sh --no-open
-> /health 检查
```

## 文档

| 主题 | 路径 |
|---|---|
| CI/CD | [docs/ci-cd/README.md](docs/ci-cd/README.md) |
| 架构 | [docs/architecture/README.md](docs/architecture/README.md) |
| 技术指南 | [docs/guide/tech-guide.md](docs/guide/tech-guide.md) |
| 使用指南 | [docs/guide/user-guide.md](docs/guide/user-guide.md) |
| 测试 | [docs/testing/README.md](docs/testing/README.md) |
