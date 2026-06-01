# 当前迭代

> 这是 Agent 的当前事实源，不保存完整流水账；历史细节看 Git 记录。

## 当前目标

保持 ChatBI Demo 可本地启动、可测试、可用中文完成问数 / 文件分析 / 管理配置 / 多 Agent 协作，并持续降低新 Agent 与同事接手成本。

## 快速状态

| 模块                        | 状态        | 备注                                                                                                  |
| --------------------------- | ----------- | ----------------------------------------------------------------------------------------------------- |
| 演示库与语义层              | ✅ 完成     | `chatbi_demo` + 语义元数据；Docker MySQL 默认 3307                                                    |
| Skill 体系                  | ✅ 完成     | semantic-query、alias-manager、decision-advisor、file-ingestion、chart/dashboard/database overview 等 |
| Agent / SSE                 | ✅ 完成     | Legacy + ReAct；支持 chart/kpi/text/error/done SSE                                                    |
| 前端对话 / 图表 / KPI       | ✅ 完成     | React 19 + ECharts 6                                                                                  |
| 会话 / 鉴权 / 记忆 / 管理页 | ✅ 完成     | 用户、数据源、LLM、多 Agents 管理                                                                     |
| 上传                        | ✅ 完成     | 文件分析                                                                                              |
| 自动化测试 / CI             | ✅ 完成     | `scripts/run_tests.py` 分套件；GitHub Actions 已配置                                                  |
| 端到端在线验收              | 🔄 按需执行 | 依赖本地数据库、后端和 LLM 可用                                                                       |

## 日常命令

| 场景          | 命令                                                                         |
| ------------- | ---------------------------------------------------------------------------- |
| 日常进场      | `bash scripts/bootstrap_dev.sh`                                              |
| 首次/依赖变动 | `bash scripts/bootstrap_dev.sh --sync`                                       |
| 代码清理      | `bash scripts/bootstrap_dev.sh --format`                                     |
| 快速测试      | `PYTHONPATH=. .venv/bin/python scripts/run_tests.py foundation -- -q`        |
| 开发启动      | `docker compose --env-file .env.dev -f docker-compose.dev.yml up -d --build` |
| 常规启动      | `docker compose up -d --build`                                               |

## 当前约定

- `.venv` 由 `uv sync` 按 `pyproject.toml` + `uv.lock` 管理；`requires-python = ">=3.11"`。
- 新增 Python 依赖只改 `pyproject.toml`，再执行 `uv lock`；Docker/CI 同样使用 `uv sync --frozen`。
- `bootstrap_dev.sh` 默认只配 Git hooks 和检查状态；不会自动跑 formatter。
- 代码改动后显式跑 `scripts/format_code.py` 或 `bootstrap_dev.sh --format`，再跑相关测试套件。
- 仅文档/说明改动不跑测试，只做必要自查。
- 新增 `tests/test_*.py` 必须先注册到 `scripts/run_tests.py` 的 `MODULE_SUITES`。

## 维护规则

- `活跃 Gap` 只保留未解决且会影响下一步执行的问题。
- `最近变更` 只保留最近 5 条；新增一条时删除最旧一条。
- 长期规则沉淀到 `AGENTS.md`、`README.md` 或对应专题文档，不放在本文件流水账里。

## 活跃 Gap

| 编号 | Gap                                                                               | 下一步                                                                                             |
| ---- | --------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| G1   | 首次切到双实例拓扑时，旧 named volume / 宿主机目录不会自动迁移或重放初始化 SQL    | 如需拿到纯净演示库与纯日志库，执行对应 compose 的 `down -v` 后再重新 `up -d --build`               |
| G3   | 在线 E2E 不进默认 CI，依赖 LLM / DB / 后端运行状态                                | 后端和 LLM 可用时跑 `python scripts/e2e_smoke.py --cases S1,S4,E1` 或按需全量                      |
| G4   | 上传文件复杂跨字段分析 / 风控建议仍偏轻量规则                                     | 如要增强，新增上传数据分析或风控建议 Skill，不复用演示库 decision-advisor                          |
| G5   | `docs/architecture/README.md` 等专题文档可能仍滞后于 guide / backend-architecture | 改动相关模块时顺手同步；主用户/技术文档在 `docs/guide/`，后端专题见 `docs/backend-architecture.md` |

## 最近变更

| 轮次 | 完成内容                                                                                                                                                 | 验证                                                                                                                                                                                      |
| ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 227  | 将 `.env.example` 调整为与 `.env.prod` 的 env 注入契约严格对齐，补清双库示例与日志库回退说明；生产 compose 补充读取 `.env.prod`；修复 `multi_agents=false` 未强制单 Agent、`ask` 澄清文案不分场景、纯图表建议误进 `demo_query` 的路由问题 | `docker compose --env-file .env.prod -f docker-compose.prod.yml config`；`PYTHONPATH=. .venv/bin/python -m pytest tests/test_multi_agent_intent.py tests/test_execution_decider.py -q`；`.venv/bin/python scripts/format_code.py` |
| 226  | 将默认管理员改为环境变量驱动：`.env*` 增加 `CHATBI_DEFAULT_ADMIN_*`，后端启动时幂等写入管理员，`init.sql` 不再硬编码 admin 密码                     | `PYTHONPATH=. .venv/bin/python -m pytest tests/test_config_db_defaults.py tests/test_default_admin_seed.py tests/test_auth_password.py -q`；`PYTHONPATH=. .venv/bin/python scripts/run_tests.py auth-memory -- -q` |
| 225  | 收敛环境变量默认模板：`.env.example` 与本地 `.env` 不再默认写入 LLM 配置，README 改为说明 LLM 可通过管理页或可选环境变量覆盖                         | 环境变量自查：确认 `.env` / `.env.example` 无 `LLM_MODEL`、`OPENAI_API_KEY`、`API_BASE`；未跑测试（仅环境模板与说明改动）                                                                |
| 224  | 将单 Agent / 多专线智能路由补成统一决策表：集中说明输入特征、`decision.mode`、`route_sequence`、切线、完成判定与 `fallback_single` / `ask` 触发条件 | 文档自查：核对 `backend/agent/execution_decider.py`、`backend/agent/multi_agent_intent.py`、`backend/agent/multi_agent_runner.py` 与 `docs/guide/tech-guide.md`、`docs/guide/agent-flow.md` |
| 223  | 同步智能路由文档到当前实现：明确聊天页默认 `multi_agents="auto"`、后端 `execution_decider` 自动分流单 Agent / 多专线 / 澄清，并补充受控 `route_sequence` 说明 | 文档自查：核对 `frontend/src/hooks/useChat.ts`、`backend/agent/runner.py`、`backend/agent/execution_decider.py`、`backend/agent/multi_agent_intent.py` 与 `docs/guide/tech-guide.md` / `user-guide.md` / `agent-flow.md` |
