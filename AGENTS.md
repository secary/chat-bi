# AGENTS.md
> 这是给 AI Agent 看的项目地图，不是给人看的百科全书。保持在 100 行以内。

## 项目简介
ChatBI 是面向银行业务场景的对话式数据分析 Demo，让用户用中文自然语言完成问数、语义别名维护和经营决策建议生成。

## 技术栈
- Backend: FastAPI + Python 3.11 + LiteLLM
- Frontend: React 18 + TypeScript + Vite + Tailwind CSS + ECharts 5
- Database: MySQL 8.0 via Docker Compose, local port 3307
- Skills: `skills/<skill-name>/SKILL.md` + deterministic Python scripts + local `mysql` CLI
- Streaming: SSE
- Quality: Python black + ruff; TypeScript ESLint + Prettier

## 快速导航
| 你想做什么 | 去哪里看 |
|-----------|---------|
| 了解系统架构与模块边界 | docs/architecture/README.md |
| 了解编码规范 | docs/conventions/README.md |
| 了解测试框架 | docs/testing/README.md |
| 了解 CI/CD | docs/ci-cd/README.md |
| 了解当前迭代 | docs/plans/current-sprint.md |
| 了解功能设计 | docs/design/ |
| 了解项目目标 | docs/goal.md |

## 硬性规则（每次执行前必须遵守）
1. 每次开始工作前，先读本文件 + docs/plans/current-sprint.md
2. 依赖方向：types/ → lib/utils/ → services/ → app/（不得反向引用）
3. 单文件不超过 300 行
4. 每个新功能必须有对应测试文件
5. 禁止使用 console.log，使用项目统一的 logger
6. API 调用统一通过封装的 apiClient，禁止裸 fetch()
7. 完成每个任务后，主动更新 docs/plans/current-sprint.md 的状态

## ChatBI 专属规则
- Skill 新增删除只改 `skills/<skill-name>/SKILL.md` 与可选 `scripts/` 文件
- 问数和决策建议脚本只执行 `SELECT`
- `chatbi-alias-manager` 只允许向 `alias_mapping` 插入已验证别名
- 决策建议必须先计算指标事实，再按确定性规则生成建议
- 数据库连接通过 `CHATBI_DB_*` 环境变量覆盖默认值
- 本地运行/测试默认优先读取 `.env.dev`（其次才是 `.env`），除非任务明确要求使用生产式环境
- 执行 Python 测试优先使用项目内 `.venv/bin/python`（Windows 用 `.venv/Scripts/python.exe`），避免落到系统 Python
- 包导入型测试优先用 `PYTHONPATH=. .venv/bin/python -m pytest ...`（Windows 对应 `.venv/Scripts/python.exe`）
- 项目 `.venv` 由 `uv` 管理，可能没有 `python -m pip`；安装/查看依赖统一用 `uv pip --python .venv/bin/python ...`
- 日常自动化测试优先用模块套件入口：`PYTHONPATH=. .venv/bin/python scripts/run_tests.py <suite>`，套件见 `docs/testing/README.md`

## 工作方式（必须遵守）
- 每次执行前：读取文件结构 + 对比验收标准 → 列出当前 Gap
- 每次执行后：运行测试 → 报告结果 → 说明下一个 Gap 是什么
- 运行测试时：优先用项目虚拟环境解释器，并确保 dev 数据库环境变量生效
- 不确定需求时：查阅 docs/design/ 对应设计文档，而不是自行假设
- 不要问我确认细节，直接执行，完成后汇报
