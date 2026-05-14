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
| 128  | 上传表自动分析增强为 LLM 语义推断 + 通用分析方法双轨；图表推荐扩展到 `horizontal_bar/grouped_bar/stacked_bar/area/scatter/heatmap/funnel/pie`；`dashboard_orchestration_core.py` 重构为通用看板聚合层，移除销售模板式写死逻辑 | `format_code.py`、`pytest tests/test_auto_analysis_skill.py tests/test_chart_recommendation_skill.py tests/test_chart_renderer.py tests/test_dashboard_orchestration_skill.py -q` |
| 129  | 上传表自动分析补齐漏斗链路：planner 可识别阶段字段并生成“转化漏斗”，执行层支持阶段型 funnel DSL，图表推荐与 renderer 同时兼容“单行多阶段”和“阶段行 + 指标值”两种漏斗输入 | `format_code.py`、`pytest tests/test_auto_analysis_skill.py tests/test_chart_recommendation_skill.py tests/test_chart_renderer.py -q` |
| 130  | 多专线改为 Manager 模式：删除路由 LLM；`multi_agent_manager` 单次规划子任务（含 depends_on 拓扑）；子 agent 收窄 ReAct/Legacy 提示词；`build_subtask_messages`；文档与 `test_multi_agent_manager` | `ruff check/format`、`pytest tests/test_multi_agent_manager.py tests/test_multi_agent_registry.py tests/test_react_runner.py -q` |
| 131  | `skills/_agents/registry.yaml` 按技能域重划 6 条子专线（上传分析、演示库问数、环比对比、图表看板、语义别名、经营建议），`max_agents_per_round` 调至 4 | `pytest tests/test_multi_agent_manager.py tests/test_admin_multi_agents.py -q` |
| 132  | `chatbi-comparison`：`detect_months` 前将「N月份」规范为「N月」，修复「1月份和2月份」无法双月解析而误走单月/跨年逻辑；新增 `test_chatbi_comparison_month_parse` | `ruff format`、`pytest tests/test_chatbi_comparison_month_parse.py -q` |
