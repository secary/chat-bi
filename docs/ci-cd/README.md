# CI/CD

ChatBI 当前落地的是 CI 自动测试：同事开发前后端功能或修复 bug 时，PR 和指定分支 push 会自动跑后端、前端检查。

## 触发条件

`.github/workflows/ci.yml` 会在以下场景触发：

- Pull Request 到 `main`
- push 到 `main`
- GitHub 手动 `workflow_dispatch`

同一个 PR 或分支重复推送会自动取消旧任务，只保留最新一次。

## 后端 CI

运行环境：

- Ubuntu latest
- Python 3.11
- `requirements.txt`

执行命令：

```bash
python scripts/run_tests.py all -- -q
```

CI 环境默认关闭或降级外部依赖：

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
- `frontend/package-lock.json`

执行命令：

```bash
cd frontend
npm ci
npm run lint
npm run test
npm run build
```

## 本地提交前建议

后端：

```bash
PYTHONPATH=. .venv/bin/python scripts/run_tests.py quick -- -q
PYTHONPATH=. .venv/bin/python scripts/run_tests.py all -- -q
```

前端：

```bash
cd frontend
npm run lint
npm run test
npm run build
```

## CD 预留

当前 workflow 不自动部署，避免误发布。后续需要 CD 时，建议新增独立 workflow：

- `deploy-dev.yml`：push 到 `dev/**` 后部署开发环境。
- `deploy-prod.yml`：仅 tag 或 GitHub Environment 审批后部署生产环境。
- 部署前强制依赖 `ChatBI CI` 成功。
