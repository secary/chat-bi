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
| G1   | `.env.example` 仍示例 `CHATBI_LOG_DB_PORT=33067`（独立日志实例），与 compose 双库同实例默认不一致 | 可选：改 `.env.example` 注释或默认值；README / `docs/guide/tech-guide` 已说明 compose 与宿主机差异 |
| G2   | Python 依赖存在 `pyproject.toml` 与 `requirements.txt` 双事实源                                   | 新增依赖时同步两处；长期可考虑 Docker/CI 也切到 `uv sync` 后移除双写                               |
| G3   | 在线 E2E 不进默认 CI，依赖 LLM / DB / 后端运行状态                                                | 后端和 LLM 可用时跑 `python scripts/e2e_smoke.py --cases S1,S4,E1` 或按需全量                      |
| G4   | 上传文件复杂跨字段分析 / 风控建议仍偏轻量规则                                                     | 如要增强，新增上传数据分析或风控建议 Skill，不复用演示库 decision-advisor                          |
| G5   | `docs/architecture/README.md` 等专题文档可能仍滞后于 guide / backend-architecture                 | 改动相关模块时顺手同步；主用户/技术文档在 `docs/guide/`，后端专题见 `docs/backend-architecture.md` |

## 最近变更

| 轮次 | 完成内容                                                                                                                                                                                                                                                                                                                                                                                                                              | 验证                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
|  |
| 157  | 收紧前端图表依赖漂移面：将 `frontend/package.json` 与 `package-lock.json` 中的 `echarts`、`echarts-for-react` 从范围版本改为精确版本 `6.0.0` / `3.0.6`，降低供应链与 wrapper/core 组合漂移风险                                                                                                                                                                                                                                        | 依赖声明改为精确版本；`frontend/package.json`、`frontend/package-lock.json` 顶层依赖已对齐                                                                                                                                                                                                                                                                                                                                                     |
| 156  | 为 Harness 补全三层追踪审计最小闭环：新增统一 `agent.harness` 事件（validated / authorized / executing / observation / finish）、trace 查询与审计规则引擎、`scripts/audit_trace.py` 命令行自检、`/admin/harness-audits` 后端接口，以及前端最小「Harness 审计」管理页入口                                                                                                                                                              | `PYTHONPATH=. .venv/bin/python -m pytest tests/test_harness_policy.py tests/test_harness_audit.py tests/test_admin_harness_audit_route.py tests/test_react_runner.py tests/test_agent_runner_contract.py tests/test_run_tests_script.py -q`；`cd frontend && npm run test`；`cd frontend && npm run lint -- src/pages/HarnessAuditPage.tsx src/types/admin.ts src/api/client.ts src/App.tsx src/components/AppLayout.tsx src/types/katex.d.ts` |
| 155  | 为单 agent ReAct 接入首版自研 Harness：新增 `harness_schema/state/policy/runner`，把 LLM 动作先做 schema 校验与 policy 授权，再进入既有 skill 执行；保留现有 `SkillResult`、SSE 与 file-ingestion / chart recommendation 等既有行为，并补 Harness 单测与 runner 集成测试                                                                                                                                                              | `PYTHONPATH=. .venv/bin/python -m pytest tests/test_harness_policy.py tests/test_react_runner.py tests/test_agent_runner_contract.py -q`                                                                                                                                                                                                                                                                                                       |
| 154  | 前端补齐上传分析结构化消息去重与热力图适配：当 `analysisProposal.markdown` 或 `dashboardReady.markdown` 与消息正文相同时，聊天气泡不再重复渲染同一段内容；同时为看板卡片和通用 `ChartRenderer` 增加 heatmap 专用布局，按坐标类别数动态增高、密集单元格自动隐藏文本，并将 `visualMap` 降为隐藏着色映射；坐标轴标签也改为识别 `YYYY-MM` / `YYYY-MM-DD` 的语义化换行并启用 `hideOverlap`，避免 cohort 留存图的月份标签机械断词和互相挤压 | `./.venv/bin/python scripts/format_code.py backend/renderers/chart.py frontend/src/components/MessageBubble.tsx frontend/src/components/ChartRenderer.tsx`；`PYTHONPATH=. .venv/bin/python -m pytest tests/test_chart_recommendation_skill.py tests/test_dashboard_orchestration_skill.py tests/test_executor_run_script.py -q`；`npm run lint -- src/components/MessageBubble.tsx src/components/ChartRenderer.tsx`                           |
