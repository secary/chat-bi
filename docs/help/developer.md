# 开发者文档

面向研发人员，说明本地开发、架构主线、测试和代码规范。

## 本地开发

- 启动开发服务：bash scripts/start_dev.sh。
- 首次或依赖变动时，start_dev 会按需执行 uv sync / npm ci。

## 测试与格式化

- 格式化：.venv/bin/python scripts/format_code.py。
- Python 快速测试：PYTHONPATH=. .venv/bin/python scripts/run_tests.py quick -- -q。
- 前端检查：cd frontend && npm run lint && npm run test && npm run build。

## 代码主线

| 主题 | 入口 |
|------|------|
| 架构边界 | docs/architecture.md |
| Agent 运行时 | docs/agent-runtime.md |
| 编码规范 | docs/conventions.md |
| 测试策略 | docs/testing.md |
