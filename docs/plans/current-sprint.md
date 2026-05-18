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
| 154  | 前端补齐上传分析结构化消息去重与热力图适配：当 `analysisProposal.markdown` 或 `dashboardReady.markdown` 与消息正文相同时，聊天气泡不再重复渲染同一段内容；同时为看板卡片和通用 `ChartRenderer` 增加 heatmap 专用布局，按坐标类别数动态增高、密集单元格自动隐藏文本，并将 `visualMap` 降为隐藏着色映射；坐标轴标签也改为识别 `YYYY-MM` / `YYYY-MM-DD` 的语义化换行并启用 `hideOverlap`，避免 cohort 留存图的月份标签机械断词和互相挤压 | `./.venv/bin/python scripts/format_code.py backend/renderers/chart.py frontend/src/components/MessageBubble.tsx frontend/src/components/ChartRenderer.tsx`；`PYTHONPATH=. .venv/bin/python -m pytest tests/test_chart_recommendation_skill.py tests/test_dashboard_orchestration_skill.py tests/test_executor_run_script.py -q`；`npm run lint -- src/components/MessageBubble.tsx src/components/ChartRenderer.tsx` |
| 153  | 为上传分析补充单表结构模板能力：`auto-analysis` 新增 `retention_cohort` 结构识别与 fallback 指标模板，可直接对 cohort 留存表生成“整体留存率趋势 / 各 cohort 留存人数 / 各 cohort 留存率热力矩阵 / 各 cohort 客户规模 / 按客户类型留存率对比”等提案；同时把留存偏移维度分组值转成 `M0/M1` 类别标签，避免热力图与趋势图被数值偏移字段误判为指标列 | `PYTHONPATH=. .venv/bin/python -m pytest tests/test_auto_analysis_skill.py tests/test_react_runner.py tests/test_chart_recommendation_skill.py tests/test_dashboard_orchestration_skill.py tests/test_executor_run_script.py -q`                                                                                                                                                                                                                                                                                                                                          |
| 152  | 继续全量收口根目录命名冲突：`auto-analysis`、`decision-advisor`、`semantic-processing` 的真实实现从 `*_core.py` 统一改名为 `engine.py`，`core.py` 保持统一入口；CLI 兼容壳、脚本入口、测试与本地模块加载全部同步到新路径，避免同进程下多个 skill 的 `engine` 同名串用 | `PYTHONPATH=. .venv/bin/python -m pytest tests/test_executor_run_script.py tests/test_react_runner.py tests/test_multi_agent_manager.py tests/test_auto_analysis_skill.py tests/test_decision_advisor_focus.py tests/test_semantic_processing_skill.py tests/test_chart_recommendation_skill.py tests/test_dashboard_orchestration_skill.py -q`                                                                                                                                                                                                                       |
| 151  | 收口图表推荐与看板编排的命名语义：将各自真正的业务实现从根目录 `*_core.py` 改名为 `engine.py`，保留 `core.py` 作为统一 skill 入口；`auto-analysis`、测试与兼容壳同步改到新路径，并用本地精确加载避免不同 skill 的 `engine` 模块名在同进程中互相串用 | `PYTHONPATH=. .venv/bin/python -m pytest tests/test_chart_recommendation_skill.py tests/test_dashboard_orchestration_skill.py tests/test_auto_analysis_skill.py tests/test_react_runner.py -q`                                                                                                                                                                                                                                                                                                                                                                             |
| 150  | 修复上传分析执行态的动态模块加载缺口：`chatbi-auto-analysis/auto_analysis_core.py` 不再依赖错误的旧层级 `sys.path` 推断来导入 `chart_recommendation_core` / `dashboard_orchestration_core`，改为按文件精确加载对应 skill 根目录模块，避免服务进程因导入顺序不同而间歇性报 `ModuleNotFoundError` | `PYTHONPATH=. .venv/bin/python -m pytest tests/test_auto_analysis_skill.py tests/test_react_runner.py tests/test_dashboard_orchestration_skill.py -q`                                                                                                                                                                                                                                                                                                                                                                                                                      |
