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
| 上传 / PDF                  | ✅ 完成     | 文件分析、PDF 降级导出                                                                                |
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

| 编号 | Gap                                                                                               | 下一步                                                                                             |
| ---- | ------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| G1   | 首次切到双实例拓扑时，旧 named volume / 宿主机目录不会自动迁移或重放初始化 SQL | 如需拿到纯净演示库与纯日志库，执行对应 compose 的 `down -v` 后再重新 `up -d --build` |
| G3   | 在线 E2E 不进默认 CI，依赖 LLM / DB / 后端运行状态                                                | 后端和 LLM 可用时跑 `python scripts/e2e_smoke.py --cases S1,S4,E1` 或按需全量                      |
| G4   | 上传文件复杂跨字段分析 / 风控建议仍偏轻量规则                                                     | 如要增强，新增上传数据分析或风控建议 Skill，不复用演示库 decision-advisor                          |
| G5   | `docs/architecture/README.md` 等专题文档可能仍滞后于 guide / backend-architecture                 | 改动相关模块时顺手同步；主用户/技术文档在 `docs/guide/`，后端专题见 `docs/backend-architecture.md` |

## 最近变更

| 轮次 | 完成内容                                                                                                                                                                                                                                                                                                                                                                                                                              | 验证                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 206  | 删除 OCR/Vision 上传识别链路：移除图片后缀上传、chat 路由 vision enrichment、`backend/vision` 模块、vision 测试套件、LLM Profile 的 vision 配置字段、相关测试注册和用户/技术文档；保留 PDF 图表转 PNG 能力 | `PYTHONPATH=. .venv/bin/python scripts/format_code.py backend/main.py backend/routes/chat_route.py backend/session_repo.py backend/memory_repo.py backend/routes/admin_llm_route.py backend/routes/admin_llm_profiles_route.py backend/llm_profile_repo.py backend/llm_settings_repo.py tests/test_llm_profile_repo.py scripts/run_tests.py`；`PYTHONPATH=. .venv/bin/python -m pytest tests/test_llm_profile_repo.py tests/test_app_llm_saved.py tests/test_chatbi_llm_fallback.py tests/test_upload_context.py tests/test_file_ingestion_skill.py tests/test_executor_file_ingestion_args.py tests/test_session_repo_payload.py -q`；`PYTHONPATH=. .venv/bin/python scripts/run_tests.py upload -- -q`；`cd frontend && npm run lint` |
| 205  | 排查 `monthly_branch_kpi.csv` 上传分析降级为审计 JSON 的问题：日志显示文件读取后未进入自动分析建议，LLM 最终总结被数字事实审计拦截；调整首轮上传分析在读到 rows 后确定性接 `chatbi-auto-analysis`，并将事实审计 fallback 改为面向用户的短提示，不再暴露原始 observation JSON | `PYTHONPATH=. .venv/bin/python scripts/format_code.py backend/agent/execution_audit.py backend/agent/react_runner.py tests/test_react_runner.py tests/test_multi_agent_runner.py`；`PYTHONPATH=. .venv/bin/python -m pytest tests/test_react_runner.py tests/test_multi_agent_runner.py tests/test_agent_skill_protocol.py tests/test_session_repo_payload.py -q`；`cd frontend && npm run lint` |
| 204  | 排查上传分析建议重复渲染：日志显示同一 trace 同时发出 `text` 与 `analysis_proposal`，普通正文包含完整建议 markdown，前端又渲染确认卡；调整 formatter 在结构化卡片存在时从 `text` 中剥离对应 markdown，仅保留“已读取文件”等摘要 | `PYTHONPATH=. .venv/bin/python scripts/format_code.py backend/agent/formatter.py tests/test_agent_skill_protocol.py`；`PYTHONPATH=. .venv/bin/python -m pytest tests/test_agent_skill_protocol.py tests/test_session_repo_payload.py -q`；`cd frontend && npm run lint` |
| 203  | 将上传附件从输入框硬编码提示词中解耦：前端上传成功后显示待发送附件条，用户自行输入提示词；发送时携带上传元数据，聊天气泡显示“已上传附件”而不暴露服务端路径；后端在内部 LLM 上下文注入附件路径并持久化附件 UI 元数据，历史加载仍保持用户原始提示词 | `PYTHONPATH=. .venv/bin/python scripts/format_code.py backend/session_repo.py backend/routes/chat_route.py tests/test_session_repo_payload.py`；`PYTHONPATH=. .venv/bin/python -m pytest tests/test_session_repo_payload.py tests/test_upload_context.py tests/test_data_source_intent.py -q`；`cd frontend && npm run lint`；`cd frontend && npm run build` 的 TypeScript 阶段通过，Vite 打包因现有 `katex/dist/katex.min.css` 解析问题失败 |
| 202  | 新增 Harness 执行模式预审计与后审计补救：`execution_decider` 输出 single / multi / ask 决策；`execution_audit` 统一 single 补救、多专线事实账本审计、汇总后数字主张审计；移除生产未引用的旧 `multi_agent_router`，并将 `upload_path_detect` / `harness_runner` 两个微型工具并回调用域；后端 `/chat` 默认 auto，聊天页移除用户侧多专线开关 | `PYTHONPATH=. .venv/bin/python scripts/format_code.py backend/agent/execution_audit.py backend/agent/data_source_intent.py backend/agent/harness_policy.py backend/agent/multi_agent_manager.py backend/agent/multi_agent_runner.py backend/agent/react_runner.py backend/agent/runner.py tests/test_execution_decider.py tests/test_multi_agent_runner.py scripts/run_tests.py`；`PYTHONPATH=. .venv/bin/python scripts/run_tests.py agent -- -q`；`PYTHONPATH=. .venv/bin/python -m pytest tests/test_data_source_intent.py tests/test_multi_agent_manager.py tests/test_harness_policy.py tests/test_react_runner.py -q`；`cd frontend && npm run lint` |
