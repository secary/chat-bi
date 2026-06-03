# CI/CD

ChatBI 当前落地的是 CI 自动测试：同事开发前后端功能或修复 bug 时，push 到功能分支或提 PR 会自动跑后端、前端检查。

## 触发条件

`.github/workflows/ci.yml` 会在以下场景触发：

- Pull Request 到 `main`（含 draft PR，覆盖所有功能分支）
- push 到 `main`（合并后验证）
- GitHub 手动 `workflow_dispatch`（无 PR 时手动触发）

同一分支重复推送会自动取消旧任务，只保留最新一次。

## 后端 CI

运行环境：

- Ubuntu latest
- Python 3.11
- `pyproject.toml` + `uv.lock`（使用 `uv sync --frozen`）
- 系统依赖：`libpango-1.0-0`、`libpangoft2-1.0-0`（WeasyPrint PDF 生成）

执行步骤：

1. **Lint**：`ruff check` + `black --check`，规则配置见 `pyproject.toml`
2. **pytest**：`.venv/bin/python scripts/run_tests.py all -- -q`

CI 环境关闭或降级外部依赖：

```text
CHATBI_AUTH_ENABLED=false
CHATBI_MEMORY_DISABLED=1
```

## 前端 CI

运行环境：

- Ubuntu latest
- Node.js 22
- `frontend/package-lock.json`（npm 缓存加速）

执行步骤：`npm run lint` → `npm run test` → `npm run build`

## 本地提交前建议

与 CI 保持一致的完整检查命令见 [docs/testing/README.md](../testing/README.md#提交前本地检查)。

## 生产 CD

`.github/workflows/deploy-prod.yml` 复用 `scripts/launch.sh` 做生产式部署。流程是：

1. checkout 要部署的 ref。
2. 部署前执行 preflight：`bash -n scripts/launch.sh`、`docker compose -f docker-compose.prod.yml config`、`python -m unittest tests.test_launch_script`。
3. 用 `tailscale/github-action@v4` 将 GitHub-hosted runner 临时接入 tailnet，并 ping `PROD_SSH_HOST` 验证可达。
4. 通过 SSH 创建远端部署目录。
5. 用 `rsync --delete` 同步仓库文件到服务器，但排除 `.env`、`.env.dev`、`.env.prod`、`.venv`、`frontend/node_modules`、`data`。
6. 如果配置了 `PROD_ENV_FILE` secret，则覆盖远端 `.env`；否则保留远端已有 `.env`，若远端没有 `.env`，`launch.sh` 会从 `.env.example` 生成。
7. 在服务器执行 `bash scripts/launch.sh --no-open --url <PROD_APP_URL> --timeout <PROD_HEALTH_TIMEOUT_SECONDS>`，由脚本负责 `docker compose -f docker-compose.prod.yml up -d --build` 和 `/health` 检查。

触发方式：

- `workflow_run`：`ChatBI CI` 在 `main` 分支成功后自动部署。
- `workflow_dispatch`：手动选择 ref 部署；可勾选 `skip_build` 来追加 `--no-build`。

`workflow_run` 触发时已经要求 `ChatBI CI` 成功；`workflow_dispatch` 手动发布时也会先跑上述 preflight，通过后才会连接服务器。

需要在 GitHub 仓库配置：

| 类型 | 名称 | 说明 |
|---|---|---|
| Secret | `PROD_SSH_HOST` | 生产服务器地址 |
| Secret | `PROD_SSH_USER` | SSH 用户 |
| Secret | `PROD_SSH_KEY` | 可登录服务器的私钥 |
| Secret | `TAILSCALE_AUTHKEY` | Tailscale auth key，建议使用 tagged、reusable、ephemeral，设备审批场景下还要 pre-approved |
| Secret | `PROD_SSH_PORT` | SSH 端口；不配置则默认 `22` |
| Secret 或 Variable | `PROD_DEPLOY_PATH` | 服务器上的部署目录 |
| Secret 或 Variable | `PROD_APP_URL` | 健康检查和访问地址；不配置则默认 `http://localhost:5173` |
| Secret | `PROD_ENV_FILE` | 可选，生产 `.env` 完整内容 |
| Variable | `PROD_HEALTH_TIMEOUT_SECONDS` | 可选，健康检查超时秒数；默认 `120` |

workflow 已绑定 GitHub Environment `chatbi-prod`。建议在该环境开启 required reviewers，这样即使 `main` CI 成功，也需要审批后才会真正发版。

如果服务器只暴露在 Tailscale 内网，`PROD_SSH_HOST` 可以直接填服务器的 `100.x.y.z` 地址或 MagicDNS 名称，GitHub runner 会先加入 tailnet 再 SSH。

如果生产机访问 Docker Hub 或海外包源超时，可在远端 `.env` 或 `PROD_ENV_FILE` 里按 `.env.dev` 同名变量覆盖镜像和构建源：

```text
MYSQL_IMAGE=m.daocloud.io/docker.io/library/mysql:8.0
PYTHON_IMAGE=m.daocloud.io/docker.io/library/python:3.11-slim
NODE_IMAGE=m.daocloud.io/docker.io/library/node:22-bookworm-slim
DEBIAN_MIRROR=https://mirrors.tuna.tsinghua.edu.cn/debian
DEBIAN_SECURITY_MIRROR=https://mirrors.tuna.tsinghua.edu.cn/debian-security
PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
NPM_REGISTRY=https://registry.npmmirror.com
```

也可以换成公司内网镜像仓库中同步好的 `node:22-bookworm-slim` 和 `python:3.11-slim`。
