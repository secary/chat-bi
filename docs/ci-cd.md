# CI/CD

ChatBI 当前落地的是 CI 自动测试：同事开发前后端功能或修复 bug 时，创建或更新到 `main` 的 PR 会自动跑后端、前端检查。

## 触发条件

`.github/workflows/ci.yml` 会在以下场景触发：

- Pull Request 到 `main`（含 draft PR，覆盖所有功能分支）
- GitHub 手动 `workflow_dispatch`（无 PR 时手动触发）

同一 PR 分支重复推送会自动取消旧任务，只保留最新一次。

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

与 CI 保持一致的完整检查命令见 [docs/testing.md](testing.md#提交前本地检查)。

## 预发 CD

`.github/workflows/deploy-pre.yml` 在 PR 合并到 `main` 后由 `push` 事件直接触发，不再等待 `main` 上的 CI。它会部署到 GitHub Environment `chatbi-pre`，并在部署后运行 E2E smoke。

Pre CD 会先按当前提交的变更文件判断是否需要重建 Docker 镜像。`backend/`、`frontend/`、`skills/`、`deploy/`、`docs/help/`、`Dockerfile`、`docker-compose.yml`、`.dockerignore`、Python/前端依赖清单等会进入镜像或影响构建上下文的变更会触发重建；只改 E2E 脚本、workflow、普通文档等不进入镜像的内容时，会优先复用预发服务器已有的 `chatbi-app` 镜像并直接进入 E2E，若远端没有旧镜像则自动回退构建。

手动 `workflow_dispatch` 固定部署 `main`，默认启用上述复用判断；取消勾选 `skip_build` 可强制重建。手动触发还可通过 `e2e_groups`、`e2e_cases`、`e2e_timeout` 临时扩大或收窄 E2E 范围，例如 `e2e_groups=all` 做完整预发验收。

同一时间只保留最新一次 pre 部署：

```yaml
concurrency:
  group: chatbi-pre-cd
  cancel-in-progress: true
```

## 生产 CD

`.github/workflows/deploy-prod.yml` 复用 `scripts/launch.sh` 做生产式部署。流程是：

1. checkout 要部署的 ref。
2. 部署前执行 preflight：`bash -n scripts/launch.sh`、`docker compose config`、`python -m unittest tests.test_launch_script`。
3. 如果配置了 `TAILSCALE_AUTHKEY`，用 `tailscale/github-action@v4` 将 GitHub-hosted runner 临时接入 tailnet，并 ping `PROD_SSH_HOST` 验证可达。
4. 通过 SSH 创建远端部署目录。
5. 用 `rsync --delete` 同步仓库文件到服务器，但排除 `.env`、`.env.dev`、`.env.prod`、`.venv`、`frontend/node_modules`、`data`。
6. 如果配置了 `PROD_ENV_FILE` secret，则覆盖远端 `.env`；否则保留远端已有 `.env`，若远端没有 `.env`，`launch.sh` 会从 `.env.example` 生成。
7. 在服务器执行 `bash scripts/launch.sh --no-open --url <PROD_APP_URL> --timeout <PROD_HEALTH_TIMEOUT_SECONDS>`，由脚本负责 `docker compose up -d --build` 和 `/health` 检查。

触发方式：

- `workflow_dispatch`：手动选择 ref 部署；可勾选 `skip_build` 来追加 `--no-build`。

生产 CD 不再监听 `main` 分支的 CI 完成事件，合并到 `main` 后不会自动部署。手动发布时会先跑上述 preflight，通过后才会连接服务器。

需要在 GitHub 仓库配置：

| 类型 | 名称 | 说明 |
|---|---|---|
| Secret | `PROD_SSH_HOST` | 生产服务器地址 |
| Secret | `PROD_SSH_USER` | SSH 用户 |
| Secret | `PROD_SSH_KEY` | 可登录服务器的私钥 |
| Secret | `TAILSCALE_AUTHKEY` | 可选；仅服务器只在 Tailscale 内网可达时配置，建议使用 tagged、reusable、ephemeral，设备审批场景下还要 pre-approved |
| Secret | `PROD_SSH_PORT` | SSH 端口；不配置则默认 `22` |
| Secret 或 Variable | `PROD_DEPLOY_PATH` | 服务器上的部署目录 |
| Secret 或 Variable | `PROD_APP_URL` | 健康检查和访问地址；不配置则默认 `http://localhost:5173` |
| Secret | `PROD_ENV_FILE` | 可选，生产 `.env` 完整内容 |
| Variable | `PROD_HEALTH_TIMEOUT_SECONDS` | 可选，健康检查超时秒数；默认 `120` |

workflow 已绑定 GitHub Environment `chatbi-prod`。建议在该环境开启 required reviewers，作为手动发版前的额外审批门禁。

如果服务器只暴露在 Tailscale 内网，`PROD_SSH_HOST` 可以直接填服务器的 `100.x.y.z` 地址或 MagicDNS 名称，GitHub runner 会先加入 tailnet 再 SSH。

如果生产机访问海外包源超时，可在远端 `.env` 或 `PROD_ENV_FILE` 里开启国内源自动择优：

```text
PACKAGE_MIRROR_CN=1
```

Docker 构建时会探测候选源并选择可用源；apt 与 pip/uv 优先国内高校/云厂商镜像，npm 优先 npmmirror、华为云，再回落官方源。Python 依赖安装会降低并发、增加超时和重试，适配较慢的部署网络。
