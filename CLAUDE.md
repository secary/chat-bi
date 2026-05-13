# CLAUDE.md

本项目 Agent 工作规则以 `AGENTS.md` 为准。

开始任何任务前，请先阅读：

- `AGENTS.md`
- `docs/plans/current-sprint.md`

## 代码改动后（Python）

在结束任务或提交前，对本次改动的 Python 范围（或与 CI 一致的全量 `backend/`、`scripts/`、`tests/`）执行：

1. **`ruff check`**（可先 `ruff check --fix` 再处理剩余告警）
2. **`ruff format`**

使用仓库根目录与虚拟环境，例如：`PYTHONPATH=. .venv/bin/python -m ruff check …`、`PYTHONPATH=. .venv/bin/python -m ruff format …`（Windows 将解释器换为 `.venv\Scripts\python.exe`）。与 `scripts/format_code.py` 不冲突，可先后执行。
