# CI/CD

ChatBI 当前落地的是 CI 自动测试：同事开发前后端功能或修复 bug 时，push 到功能分支或提 PR 会自动跑后端、前端检查。

## 触发条件

`.github/workflows/ci.yml` 会在以下场景触发：

- push 到 `main`、`dev**`、`test**`
- Pull Request 到 `main`
- GitHub 手动 `workflow_dispatch`

同一分支重复推送会自动取消旧任务，只保留最新一次。

## 后端 CI

运行环境：

- Ubuntu latest
- Python 3.11
- `requirements.txt`（pip 缓存加速）
- 系统依赖：`libpango-1.0-0`、`libpangoft2-1.0-0`（WeasyPrint PDF 生成）

执行步骤：

1. **Lint**：`ruff check` + `black --check`，规则配置见 `pyproject.toml`
2. **pytest**：`python scripts/run_tests.py all -- -q`

CI 环境关闭或降级外部依赖：

```text
CHATBI_AUTH_ENABLED=false
CHATBI_MEMORY_DISABLED=1
CHATBI_VISION_DISABLED=1
CHATBI_PDF_SUMMARY_DISABLED=1
```

## 前端 CI

运行环境：

- Ubuntu latest
- Node.js 22
- `frontend/package-lock.json`（npm 缓存加速）

执行步骤：`npm run lint` → `npm run test` → `npm run build`

## 本地提交前建议

与 CI 保持一致的完整检查命令见 [docs/testing/README.md](../testing/README.md#提交前本地检查)。

## CD 预留

当前 workflow 不自动部署，避免误发布。后续需要 CD 时，建议新增独立 workflow：

- `deploy-dev.yml`：push 到 `dev/**` 后部署开发环境。
- `deploy-prod.yml`：仅 tag 或 GitHub Environment 审批后部署生产环境。
- 部署前强制依赖 `ChatBI CI` 成功。
