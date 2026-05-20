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
| 上传 / Vision / PDF         | ✅ 完成     | 文件分析、图像抽取门禁、PDF 降级导出                                                                  |
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
- `requirements.txt` 仅保留给 Docker/CI 兼容；新增 Python 依赖必须同步 `pyproject.toml`、`requirements.txt`，再执行 `uv lock`。
- `bootstrap_dev.sh` 默认只配 Git hooks 和检查状态；不会自动跑 formatter。
- 代码改动后显式跑 `scripts/format_code.py` 或 `bootstrap_dev.sh --format`，再跑相关测试套件。
- 仅文档/说明改动不跑测试，只做必要自查。
- 新增 `tests/test_*.py` 必须先注册到 `scripts/run_tests.py` 的 `MODULE_SUITES`。

## 维护规则

- `活跃 Gap` 只保留未解决且会影响下一步执行的问题。
- `最近变更` 只保留最近 5 条；新增一条时删除最旧一条。
- 长期规则沉淀到 `AGENTS.md`、`README.md` 或对应专题文档，不放在本文件流水账里。

## 活跃 Gap

| 编号 | Gap                                                                                               | 下一步                                                                                             |
| ---- | ------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| G1   | 首次切到双实例拓扑时，旧 named volume / 宿主机目录不会自动迁移或重放初始化 SQL | 如需拿到纯净演示库与纯日志库，执行对应 compose 的 `down -v` 后再重新 `up -d --build` |
| G2   | Python 依赖存在 `pyproject.toml` 与 `requirements.txt` 双事实源                                   | 新增依赖时同步两处；长期可考虑 Docker/CI 也切到 `uv sync` 后移除双写                               |
| G3   | 在线 E2E 不进默认 CI，依赖 LLM / DB / 后端运行状态                                                | 后端和 LLM 可用时跑 `python scripts/e2e_smoke.py --cases S1,S4,E1` 或按需全量                      |
| G4   | 上传文件复杂跨字段分析 / 风控建议仍偏轻量规则                                                     | 如要增强，新增上传数据分析或风控建议 Skill，不复用演示库 decision-advisor                          |
| G5   | `docs/architecture/README.md` 等专题文档可能仍滞后于 guide / backend-architecture                 | 改动相关模块时顺手同步；主用户/技术文档在 `docs/guide/`，后端专题见 `docs/backend-architecture.md` |

## 最近变更

| 轮次 | 完成内容                                                                                                                                                                                                                                                                                                                                                                                                                              | 验证                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 163  | 继续收紧后台心智负担：前端移除“多 Agents 管理”常规入口，并将审计页统一改为更产品化的“审计”；聊天页 admin trace 跳转也改到 `/audits`，同时保留 `/harness-audits` 与旧 `/multi-agents` 的兼容重定向，避免历史链接失效                                                                                                                                                                                                                | `cd frontend && npm run lint -- src/App.tsx src/components/AppLayout.tsx src/pages/ChatPage.tsx src/pages/HarnessAuditPage.tsx`                                                                                                                                                                                                                                                                                                               |
| 162  | 收紧多 Agents 管理权限边界：运行时 registry 新增 `enabled` 开关，只有启用的专线才会进入系统内部候选集；`/admin/multi-agents` 的 PUT 也改为仅接受安全运行时配置（每轮子任务上限、Manager 最大轮数、各专线 enabled），不再允许前端修改 role prompt、技能清单、禁用技能或增删专线；前端“多 Agents 管理”页同步改成只读观察台，只保留启用状态与全局开关 | `PYTHONPATH=. .venv/bin/python scripts/format_code.py backend/agent/multi_agent_registry.py backend/routes/admin_multi_agents_route.py tests/test_admin_multi_agents.py tests/test_multi_agent_registry.py`；`PYTHONPATH=. .venv/bin/python -m pytest tests/test_admin_multi_agents.py tests/test_multi_agent_registry.py tests/test_multi_agent_manager.py tests/test_multi_agent_runner.py tests/test_run_tests_script.py -q`；`cd frontend && npm run lint -- src/pages/MultiAgentsAdminPage.tsx src/types/admin.ts src/api/client.ts` |
| 161  | 将多 Agent registry 从“写死技能白名单”扩展为“默认动态调用 + 可选 restricted”：新增 `skill_mode`（`dynamic` / `restricted`）与 `blocked_skills`，其中 `skills` 在动态模式下改为优先技能；运行时 `skills_for_agent()` 现在可按模式返回动态候选集，Manager 能力说明与前端多 Agents 管理页也同步支持“动态可调 / 白名单 / 禁用技能”配置 | `PYTHONPATH=. .venv/bin/python scripts/format_code.py backend/agent/multi_agent_registry.py backend/agent/multi_agent_manager.py backend/routes/admin_multi_agents_route.py tests/test_admin_multi_agents.py tests/test_multi_agent_registry.py`；`PYTHONPATH=. .venv/bin/python -m pytest tests/test_admin_multi_agents.py tests/test_multi_agent_registry.py tests/test_multi_agent_manager.py tests/test_multi_agent_runner.py tests/test_run_tests_script.py -q`；`cd frontend && npm run lint -- src/pages/MultiAgentsAdminPage.tsx src/types/admin.ts` |
| 160  | 按演示环境统一为“双库双实例”并做数据库瘦身：`docker-compose.yml` / `docker-compose.dev.yml` 都改为 `demo-mysql`（named volume，仅承载 `chatbi_demo`）+ `log-mysql`（宿主机目录，仅承载 `chatbi_local_logs`）；`database/init.sql` 回归单业务演示库并默认写入 `admin` / `admin123`；同时移除 `database/migrations/*`、`external_bank_*.sql`、`tests/test_external_bank_demo_sql.py` 和外部数据源相关文档，补充新的 `database/README.md` 说明当前目录职责 | `PYTHONPATH=. .venv/bin/python -m pytest tests/test_config_db_defaults.py tests/test_db_mysql_targets.py tests/test_trace.py tests/test_database_overview_skill.py -q` |
| 159  | 为缓解 macOS Spotlight 对 MySQL 宿主机挂载目录的干扰，并统一演示环境拓扑，调整 `docker-compose.dev.yml` 与 `docker-compose.yml`：主业务库 `demo-mysql` 改用 Docker named volume，独立 `log-mysql` 仅持久化 `chatbi_local_logs` 到 `database/mysql-data-log/`；`database/init.sql` 保持 `chatbi_demo` 单业务演示库并默认初始化 `admin` / `admin123`，同时同步 README / 架构文档说明新的双库结构 | `PYTHONPATH=. .venv/bin/python -m pytest tests/test_config_db_defaults.py tests/test_db_mysql_targets.py tests/test_trace.py -q` |
