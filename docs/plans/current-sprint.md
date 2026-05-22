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
| 177  | 修复审计页“最近 Trace”列表被无关单事件日志污染的问题：后端最近候选改为只保留真正进入聊天/agent 执行链路的 trace（`http.chat`、`agent.*`、`skill.*`），过滤 `sessions`、`dashboard.overview`、`admin.harness_audit` 等页面访问日志，方便直接定位最新聊天的审计记录 | `PYTHONPATH=. .venv/bin/python scripts/format_code.py backend/trace_repo.py tests/test_trace_repo.py scripts/run_tests.py`；`PYTHONPATH=. .venv/bin/python -m pytest tests/test_trace_repo.py tests/test_run_tests_script.py tests/test_admin_harness_audit_route.py tests/test_harness_audit.py -q` |
| 176  | 继续增强经营建议审计可见性：为 `decision_content_audit` 增加独立 `decision_content_audited` Harness 事件，前端 Debug 时间线可直接搜索并显示 `audit=ok/issues=0` 等摘要；问题列表中的 `DECISION_*` 也改为跳到该专门事件。同时确认多专线专线错拿技能的根因来自 dynamic 模式暴露其他已启用技能，前一轮已通过 `restricted` 白名单模式从源头收紧 | `PYTHONPATH=. .venv/bin/python scripts/format_code.py backend/agent/harness_events.py backend/agent/react_runner.py backend/agent/multi_agent_runner.py`；`PYTHONPATH=. .venv/bin/python -m pytest tests/test_harness_audit.py tests/test_decision_content_audit.py tests/test_multi_agent_registry.py tests/test_multi_agent_runner.py tests/test_admin_harness_audit_route.py -q`；`cd frontend && npm run test -- src/lib/auditDebug.test.ts`；`cd frontend && npm run lint -- src/lib/auditDebug.ts src/lib/auditDebug.test.ts src/pages/HarnessAuditPage.tsx src/components/HarnessBusinessFlowCard.tsx src/types/admin.ts` |
| 175  | 将“决策建议内容审核”从仅在问题列表报错升级为可见状态卡：即使 `decision_content_audit` 无 issue，也会在审计页显示“决策建议内容审核”卡并标明通过；同时收紧多专线 registry，把上传分析、演示库问数、环比对比、图表看板、语义别名、经营建议等专线统一切到 `restricted` 白名单模式，避免 `demo_query` 线误拿到 `chatbi-decision-advisor` 之类的错线技能 | `PYTHONPATH=. .venv/bin/python scripts/format_code.py backend/agent/harness_business_flows.py backend/agent/harness_business_flows_decision.py tests/test_harness_audit.py`；`PYTHONPATH=. .venv/bin/python -m pytest tests/test_harness_audit.py tests/test_decision_content_audit.py tests/test_multi_agent_registry.py tests/test_multi_agent_runner.py tests/test_admin_harness_audit_route.py -q`；`cd frontend && npm run lint -- src/pages/HarnessAuditPage.tsx src/components/HarnessBusinessFlowCard.tsx src/types/admin.ts` |
| 174  | 在 Harness 审计中补上首版“决策建议内容审核”：`chatbi-decision-advisor` 结果返回后会基于 `facts` / `advices` 做规则审计，并把 `FACTS_MISSING_FOR_DECISION`、`DECISION_ADVICE_TOO_GENERIC`、`DECISION_ADVICE_NOT_GROUNDED`、`DECISION_SCOPE_MISMATCH` 等风险同步抬升到审计报告问题列表，便于在生成链路之外再看一层建议内容本身是否可靠 | `PYTHONPATH=. .venv/bin/python scripts/format_code.py backend/agent/decision_content_audit.py backend/agent/harness_audit_rules.py backend/agent/react_runner.py backend/agent/multi_agent_runner.py tests/test_decision_content_audit.py tests/test_harness_audit.py scripts/run_tests.py`；`PYTHONPATH=. .venv/bin/python -m pytest tests/test_decision_content_audit.py tests/test_harness_audit.py tests/test_multi_agent_runner.py tests/test_admin_harness_audit_route.py tests/test_run_tests_script.py -q`；`cd frontend && npm run lint -- src/pages/HarnessAuditPage.tsx src/components/HarnessBusinessFlowCard.tsx src/types/admin.ts` |
| 173  | 继续为 Harness 审计补第二张“业务链路状态卡”：新增演示库问数链路状态卡，基于 `chatbi-semantic-query` 的 `plan_summary`、`row_count`、`chart_plan`、`kpis` 等结果信号，汇总“语义命中 / 查询规划 / 结果取回 / 图表-KPI”四步状态，让管理员能直接看出问数卡在语义识别、结果为空还是仅停在表格结果阶段 | `PYTHONPATH=. .venv/bin/python scripts/format_code.py backend/agent/harness_business_flows.py backend/agent/harness_business_flows_semantic.py backend/agent/react_runner.py backend/agent/multi_agent_runner.py tests/test_harness_audit.py`；`PYTHONPATH=. .venv/bin/python -m pytest tests/test_harness_audit.py tests/test_multi_agent_runner.py tests/test_admin_harness_audit_route.py -q`；`cd frontend && npm run lint -- src/pages/HarnessAuditPage.tsx src/components/HarnessBusinessFlowCard.tsx src/types/admin.ts` |
