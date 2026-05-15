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

| 轮次 | 完成内容                                                                                                             | 验证                                                                                        |
| ---- | -------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| 134  | 多 Agent 问数：同一列多枚举过滤合并为 `IN`；`chatbi-semantic-query` 入参优先取「用户原述」；ReAct/单次规划 JSON 解析失败不再抛裸异常；空结果 Observation 附 SQL 与互斥条件提示 | `ruff check/format`、`pytest tests/test_semantic_query_core.py tests/test_executor_file_ingestion_args.py tests/test_observation.py tests/test_planner_parse_json.py -q` |
| 135  | 经营建议 KPI 全 0：`chatbi-decision-advisor` 与问数共用「用户原述」入参；解析「2026 年前四个月」时间窗；决策 SQL WHERE 同列多 `=` 合并为 `IN` | `ruff check/format`、`pytest tests/test_decision_advisor_focus.py tests/test_executor_file_ingestion_args.py -q` |
| 136  | 多 Agent 上传采纳看板：宽度随主栏自适应；KPI/图表按数量与断点网格排布（单指标全宽+大屏双列），表头与卡片 `min-w-0` 防溢出 | `frontend` ESLint |
| 137  | Manager：`上传路径/采纳/上传提案` 会话线索注入规划；system 增加路由硬约束与专线技能边界；`test_multi_agent_manager` 覆盖线索与 LLM 入参 | `ruff check/format`、`pytest tests/test_multi_agent_manager.py -q` |
| 138  | `load_messages_ui` 恢复 `dashboardReady`/`analysisProposal`/`planSummary`，离开聊天页再返回可看板；`test_session_repo_payload` | `pytest tests/test_session_repo_payload.py -q`、`ruff` |
