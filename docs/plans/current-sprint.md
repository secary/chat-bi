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

| 编号 | Gap                                                                                                    | 下一步                                                                                             |
| ---- | ------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------- |
| G1   | 日志库连接已改回 dev 主 MySQL 实例双库模式，README 与专题文档仍可能残留旧的外部 33067 或独立日志库表述 | 调整日志库相关文档，明确 dev 环境默认由 `demo-mysql` 同时承载 `chatbi_demo` 与 `chatbi_local_logs` |
| G2   | Python 依赖存在 `pyproject.toml` 与 `requirements.txt` 双事实源                                        | 新增依赖时同步两处；长期可考虑 Docker/CI 也切到 `uv sync` 后移除双写                               |
| G3   | 在线 E2E 不进默认 CI，依赖 LLM / DB / 后端运行状态                                                     | 后端和 LLM 可用时跑 `python scripts/e2e_smoke.py --cases S1,S4,E1` 或按需全量                      |
| G4   | 上传文件复杂跨字段分析 / 风控建议仍偏轻量规则                                                          | 如要增强，新增上传数据分析或风控建议 Skill，不复用演示库 decision-advisor                          |
| G5   | 部分历史文档可能仍有旧环境或旧多库表述                                                                 | 改动相关模块时顺手同步 README、docs/architecture、docs/tech-guide                                  |

## 最近变更

| 轮次 | 完成内容                                                                                                                                                                                                                                                                          | 验证                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| ---- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 152  | 继续全量收口根目录命名冲突：`auto-analysis`、`decision-advisor`、`semantic-processing` 的真实实现从 `*_core.py` 统一改名为 `engine.py`，`core.py` 保持统一入口；CLI 兼容壳、脚本入口、测试与本地模块加载全部同步到新路径，避免同进程下多个 skill 的 `engine` 同名串用 | `PYTHONPATH=. .venv/bin/python -m pytest tests/test_executor_run_script.py tests/test_react_runner.py tests/test_multi_agent_manager.py tests/test_auto_analysis_skill.py tests/test_decision_advisor_focus.py tests/test_semantic_processing_skill.py tests/test_chart_recommendation_skill.py tests/test_dashboard_orchestration_skill.py -q`                                                                                                                                                                                                                       |
| 151  | 收口图表推荐与看板编排的命名语义：将各自真正的业务实现从根目录 `*_core.py` 改名为 `engine.py`，保留 `core.py` 作为统一 skill 入口；`auto-analysis`、测试与兼容壳同步改到新路径，并用本地精确加载避免不同 skill 的 `engine` 模块名在同进程中互相串用 | `PYTHONPATH=. .venv/bin/python -m pytest tests/test_chart_recommendation_skill.py tests/test_dashboard_orchestration_skill.py tests/test_auto_analysis_skill.py tests/test_react_runner.py -q`                                                                                                                                                                                                                                                                                                                                                                             |
| 150  | 修复上传分析执行态的动态模块加载缺口：`chatbi-auto-analysis/auto_analysis_core.py` 不再依赖错误的旧层级 `sys.path` 推断来导入 `chart_recommendation_core` / `dashboard_orchestration_core`，改为按文件精确加载对应 skill 根目录模块，避免服务进程因导入顺序不同而间歇性报 `ModuleNotFoundError` | `PYTHONPATH=. .venv/bin/python -m pytest tests/test_auto_analysis_skill.py tests/test_react_runner.py tests/test_dashboard_orchestration_skill.py -q`                                                                                                                                                                                                                                                                                                                                                                                                                      |
| 149  | 对齐 `PR46` 的上传分析 follow-up 链路：`list_messages_for_llm` 保留 `analysisProposal/dashboardReady` 结构化 payload，`react_runner` 在“采纳全部指标”时优先复用上一轮 proposal 的 `proposed_metrics` 与缓存 rows 直达 `chatbi-auto-analysis` 执行态，不再回退到重复 `file-ingestion`；sessionless 前端历史也同步携带 proposal/dashboard 元数据 | `PYTHONPATH=. .venv/bin/python -m pytest tests/test_react_runner.py tests/test_session_repo_payload.py tests/test_auto_analysis_skill.py tests/test_dashboard_orchestration_skill.py -q`                                                                                                                                                                                                                                                                                                                                                                                   |
| 148  | 将剩余 helper 从 `scripts/` 迁到各 skill 根目录：新增根级 `*_core.py` / `semantic_query/` / `inspect_uploaded_table.py` 等真实实现，`core.py` 与测试统一切到新位置；原 `scripts/` 中的 helper 文件退化为兼容壳，`chatbi-comparison`、`file-ingestion` 等脚本入口也收成 CLI 转发层 | `PYTHONPATH=. .venv/bin/python -m pytest tests/test_auto_analysis_skill.py tests/test_semantic_processing_skill.py tests/test_chart_recommendation_skill.py tests/test_dashboard_orchestration_skill.py tests/test_chatbi_comparison_month_parse.py tests/test_decision_advisor_focus.py tests/test_semantic_query_core.py tests/test_database_overview_skill.py tests/test_metric_explainer_skill.py tests/test_file_ingestion_skill.py tests/test_executor_run_script.py tests/test_react_runner.py tests/test_multi_agent_manager.py -q`                                    |
