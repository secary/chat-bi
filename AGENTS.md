# AGENTS.md
> Agent 项目地图，保持短、准、可执行。

## 项目
ChatBI 是银行场景的对话式数据分析 Demo，支持中文问数、语义别名维护、经营建议、上传文件分析、仪表盘和多 Agent 协作。

## 栈
- Backend: FastAPI + Python 3.11+ + LiteLLM
- Frontend: React 19 + TypeScript + Vite + Tailwind CSS + ECharts 6
- Database: MySQL 8.0 via Docker Compose，本地默认 3307
- Skills: `skills/<skill-name>/SKILL.md` + deterministic Python scripts
- Quality: ruff + black + ESLint；测试入口 `scripts/run_tests.py`

## 导航
| 主题 | 文件 |
|---|---|
| 架构/边界 | docs/architecture/README.md |
| 编码规范 | docs/conventions/README.md |
| 测试/CI | docs/testing/README.md、docs/ci-cd/README.md |
| 当前迭代 | docs/plans/current-sprint.md |
| 设计 | docs/design/ |

## 快速进入
- 首次或依赖变动：`bash scripts/bootstrap_dev.sh --sync`
- 日常进场：`bash scripts/bootstrap_dev.sh`
- 本地清理：`bash scripts/bootstrap_dev.sh --format`
- 快速测试：`PYTHONPATH=. .venv/bin/python scripts/run_tests.py foundation -- -q`
- 开发启动：`docker compose --env-file .env.dev -f docker-compose.dev.yml up -d --build`

## 必守规则
- 开始工作先读本文件和 `docs/plans/current-sprint.md`，再按任务需要查对应 docs/design。
- 依赖方向：types/ → lib/utils/ → services/ → app/；禁止反向引用。
- 单文件不超过 300 行；新功能必须补测试并注册到 `scripts/run_tests.py` 的 `MODULE_SUITES`。
- 禁止 `console.log`；前端 API 统一走 `apiClient`，禁止裸 `fetch()`。
- Python 测试优先用 `.venv/bin/python`；本地环境默认 `.env.dev` 优先，其次 `.env`。
- `.venv` 由 `uv sync` 按 `pyproject.toml` + `uv.lock` 管理；`requirements.txt` 仅兼容 Docker/CI。
- 新增 Python 依赖必须同步 `pyproject.toml`、`requirements.txt`，再执行 `uv lock`。
- Skill 新增/删除只改 `skills/<skill-name>/SKILL.md` 与可选 `scripts/`；问数/决策脚本只执行 `SELECT`。
- 代码改动后跑 `scripts/format_code.py` 和相关测试套件；文档/说明小改可只跑最小相关校验。
- 完成任务后更新 `docs/plans/current-sprint.md` 的 Gap 记录。
