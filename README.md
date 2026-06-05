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
CHATBI_SEED_USERS=root:强密码:root
```

### 3. 可选：配置国内源

如果服务器访问海外包源不稳定，可在 `.env` 里开启国内源自动择优：

```dotenv
PACKAGE_MIRROR_CN=1
```

Docker 构建时会探测候选源并选择可用源；apt 与 pip/uv 优先国内高校/云厂商镜像，npm 优先 npmmirror、华为云，再回落官方源。

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

仓库已提供 `.github/workflows/deploy-prod.yml`，生产部署仅支持手动 `workflow_dispatch`。

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
| CI/CD | [docs/ci-cd.md](docs/ci-cd.md) |
| 架构 | [docs/architecture.md](docs/architecture.md) |
| Agent 运行时 | [docs/agent-runtime.md](docs/agent-runtime.md) |
| 页面帮助 | [docs/help/](docs/help/) |
| 测试 | [docs/testing.md](docs/testing.md) |
