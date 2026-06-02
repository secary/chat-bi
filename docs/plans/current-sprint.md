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
| G1   | 从旧双 MySQL / 双 schema 拓扑切回单 schema 时，旧 `database/mysql-data-log/` 和旧日志库不会自动迁移 | 如需保留旧日志，先导出旧 `chatbi_local_logs.log` 后导入 `chatbi_demo`；纯净演示可 `down -v` 后重建 |
| G3   | 在线 E2E 不进默认 CI，依赖 LLM / DB / 后端运行状态                                | 后端和 LLM 可用时跑 `python scripts/e2e_smoke.py --cases S1,S4,E1` 或按需全量                      |
| G4   | 上传文件复杂跨字段分析 / 风控建议仍偏轻量规则                                     | 如要增强，新增上传数据分析或风控建议 Skill，不复用演示库 decision-advisor                          |
| G5   | `docs/architecture/README.md` 等专题文档可能仍滞后于 guide / backend-architecture | 改动相关模块时顺手同步；主用户/技术文档在 `docs/guide/`，后端专题见 `docs/backend-architecture.md` |

## 最近变更

| 轮次 | 完成内容                                                                                                                                                 | 验证                                                                                                                                                                                      |
| ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 232  | 因 `app` / `db` 容器名过短易与其他项目冲突，恢复 compose 服务名和容器名：dev 数据库为 `chatbi-db-dev`，prod 数据库为 `chatbi-db`，开发应用为 `chatbi-app-dev`，生产应用为 `chatbi-app` | `docker compose --env-file .env.dev -f docker-compose.dev.yml config --services`；`docker compose -f docker-compose.prod.yml config --services`；`git diff --check` |
| 231  | 将开发态也收敛为一体应用容器：根 `Dockerfile` 新增 `dev` stage，`chatbi-app-dev` 容器内同时运行 Vite dev server 与 FastAPI reload server；`docker-compose.dev.yml` 从 backend/frontend 两服务合并为 `chatbi-app`，保留 `5174` 前端入口与 `8001` 后端调试入口；删除旧 `backend/Dockerfile`、`frontend/Dockerfile`、前端 dev entrypoint、前端 nginx 配置与前端 Docker ignore | `docker compose --env-file .env.dev -f docker-compose.dev.yml config`；`docker compose -f docker-compose.prod.yml config`；`.venv/bin/python scripts/format_code.py` |
| 230  | 将生产式本地部署收敛为前后端一体镜像：新增根 `Dockerfile` 多阶段构建前端并安装后端运行时，`chatbi-app` 容器内同时运行 nginx + FastAPI，nginx 通过同源 `/api` 反代本容器后端；`docker-compose.prod.yml` 从 backend/frontend 两服务合并为 `chatbi-app`，仅对外暴露 `5173` | `docker compose -f docker-compose.prod.yml config`；`.venv/bin/python scripts/format_code.py` |
| 229  | 合并 Git ignore 配置：将 `frontend/.gitignore` 的前端日志、Node/Vite 产物和编辑器规则迁入根 `.gitignore`，删除子目录 `.gitignore`，保留 Docker ignore 独立服务 build context | `git check-ignore -v frontend/node_modules/foo frontend/dist/index.html frontend/dist-ssr/a.js frontend/.env.local frontend/npm-debug.log logs/a.log`；`find . -maxdepth 3 -name .gitignore -print` |
| 228  | 将日志库从独立 `log-mysql` 实例迁回主库：dev/prod compose 仅启动一个数据库容器，`init.sql` 只初始化 `chatbi_demo`；应用/管理表去掉 `chatbi_` 前缀后改为 `app_*` / `admin_*`，日志表改为 `log`；数据库容器对宿主机暴露端口为 dev `33067`、prod `3307`，容器内仍使用 MySQL 标准 `3306`；日志连接默认复用 `CHATBI_DB_HOST/PORT/USER/PASSWORD/NAME`；同步 README、数据库说明、用户/技术/架构文档 | `docker compose -f docker-compose.prod.yml config`；`docker compose --env-file .env.dev -f docker-compose.dev.yml config`；`PYTHONPATH=. .venv/bin/python -m pytest tests/test_config_db_defaults.py tests/test_trace.py tests/test_trace_repo.py -q`；`PYTHONPATH=. .venv/bin/python scripts/run_tests.py auth-memory -- -q` |
| 227  | 将 `.env.example` 调整为与 `.env.prod` 的 env 注入契约严格对齐，补清双库示例与日志库回退说明；生产 compose 补充读取 `.env.prod`；修复 `multi_agents=false` 未强制单 Agent、`ask` 澄清文案不分场景、纯图表建议误进 `demo_query`、图表形式建议被误判为经营建议、事实审计兜底误称上传文件和月份数字误伤、跨月画图 / 月份明细查询被单值聚合、汇总文字审计失败时吞掉已审计图表的路由 / 审计 / 图表问题；前端处理进度不再展示 raw thinking 数量 | `docker compose --env-file .env.prod -f docker-compose.prod.yml config`；`PYTHONPATH=. .venv/bin/python -m pytest tests/test_multi_agent_runner.py tests/test_semantic_query_core.py tests/test_multi_agent_intent.py tests/test_execution_decider.py tests/test_data_source_intent.py -q`；`PYTHONPATH=. .venv/bin/python -m pytest tests/test_multi_agent_intent.py tests/test_execution_decider.py -q`；`.venv/bin/python scripts/format_code.py` |
