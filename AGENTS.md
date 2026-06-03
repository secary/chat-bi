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
| GitHub 在线 Agent | .github/copilot-instructions.md、.github/agents/ |
| 依赖安全 | .github/dependabot.yml、.github/workflows/ |

## 快速进入
- 首次或依赖变动：`bash scripts/bootstrap_dev.sh --sync`
- 日常进场：`bash scripts/bootstrap_dev.sh`
- 本地清理：`bash scripts/bootstrap_dev.sh --format`
- 快速测试：`PYTHONPATH=. .venv/bin/python scripts/run_tests.py foundation -- -q`
- 开发启动：`bash scripts/start_dev.sh`（开发库、后端、前端都跑宿主机；默认 compose 仍保留生产式数据库容器）

## 必守规则
- 开始工作先读本文件和 `docs/plans/current-sprint.md`，再按任务需要查对应 docs/design。
- 依赖方向：types/ → lib/utils/ → services/ → app/；禁止反向引用。
- 单文件不超过 300 行；新功能必须补测试并注册到 `scripts/run_tests.py` 的 `MODULE_SUITES`。
- 禁止 `console.log`；前端 API 统一走 `apiClient`，禁止裸 `fetch()`。
- Python 测试优先用 `.venv/bin/python`；后端通用加载只读 `.env`，本地开发由 `scripts/start_dev.sh` 显式读取 `.env.dev`。
- `.venv` 由 `uv sync` 按 `pyproject.toml` + `uv.lock` 管理。
- 新增 Python 依赖只改 `pyproject.toml`，再执行 `uv lock`。
- Skill 新增/删除只改 `skills/<skill-name>/SKILL.md` 与可选 `scripts/`；问数/决策脚本只执行 `SELECT`。
- 代码改动后跑 `scripts/format_code.py` 和相关测试套件；仅文档/说明改动不跑测试，只做必要自查。
- 完成任务后更新 `docs/plans/current-sprint.md` 的 Gap 记录。

## GitHub 在线协作
- 仓库级 Copilot 在线说明：`.github/copilot-instructions.md`
- 测试专职 Agent：`.github/agents/testing-specialist.agent.md`
- 文档专职 Agent：`.github/agents/docs-specialist.agent.md`
- 若在 GitHub 在线模式分派任务，优先按职责选择对应 agent，避免测试和文档职责混改。

## 依赖与供应链
- 已接入 Dependabot 配置：`.github/dependabot.yml`，覆盖 Python、npm、GitHub Actions、Docker；当前按月检查，且每类最多保留 1 个开放 PR 以降低噪音。
- 已接入 PR 供应链检查：`.github/workflows/dependency-review.yml`，其中 Python 走 `uv export --frozen` + `pip-audit`，前端走 `npm audit --audit-level=high`。
- Dependabot 主要降低“已知漏洞依赖长期不更新”和“Action / 基础镜像版本漂移”风险，不等于完全防止供应链投毒。
- Python 依赖现已收敛为 `pyproject.toml` + `uv.lock` 双事实源；处理 Dependabot Python PR 时要确认 manifest 与 lockfile 一致更新。
- 需要仓库管理员在 GitHub Settings 里确认 4 个开关已开启：Dependency graph、Dependabot alerts、Dependabot security updates、Secret scanning。
- 如果要真正形成门禁，把 `Supply Chain Audit` 工作流设为受保护分支的 required status check；否则它只会报警，不会阻止合并。
