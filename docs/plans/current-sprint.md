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
| 167  | 对审计页 Debug 视图做轻收敛：为事件时间线增加“关键事件 / 关注事件 / 普通事件”分层展示，并将问题列表和调试事件联动起来；管理员现在可从 `HARNESS_POLICY_REJECTED`、`DOWNSTREAM_DATA_MISSING`、`SUMMARY_WITH_UNMET_DEPENDENCY` 等 issue 一键跳到对应 debug 搜索结果，减少手动猜关键词和滚动查找成本 | `cd frontend && npm run test -- src/lib/auditDebug.test.ts`；`cd frontend && npm run lint -- src/pages/HarnessAuditPage.tsx src/lib/auditDebug.ts src/lib/auditDebug.test.ts` |
| 166  | 审计页新增首版 Debug 模式：在 `/audits` 里可展开 trace 时间线，按 event_name / agent / skill / reason / payload 搜索调试事件，并按卡片查看 `span_name`、`event_name`、关键上下文字段和原始 payload；同时补了 `auditDebug` 前端 helper，用于事件摘要、筛选与 payload 展示，降低管理员排障时必须进 Network/数据库的频率 | `cd frontend && npm run test -- src/lib/auditDebug.test.ts`；`cd frontend && npm run lint -- src/pages/HarnessAuditPage.tsx src/lib/auditDebug.ts src/lib/auditDebug.test.ts` |
| 165  | 为多 Agent 补上首版后审计闭环：specialist observation 现在会额外记录 `has_result`、`has_rows`、`has_auto_analysis`、`dependency_warning` 等结果质量标记；Manager 在依赖未满足却仍进入汇总前，会写入 `summary_dependency_unmet` 审计事件；审计规则新增“specialist 无有效结果”“下游依赖缺失”“依赖未满足仍汇总”三类问题检测，帮助区分“能执行”和“真正产出可用结果” | `PYTHONPATH=. .venv/bin/python scripts/format_code.py backend/agent/harness_events.py backend/agent/multi_agent_runner.py backend/agent/harness_audit_rules.py tests/test_harness_audit.py tests/test_multi_agent_runner.py`；`PYTHONPATH=. .venv/bin/python -m pytest tests/test_harness_audit.py tests/test_multi_agent_runner.py tests/test_multi_agent_manager.py tests/test_react_runner.py tests/test_harness_policy.py tests/test_run_tests_script.py -q` |
| 164  | 为多专线 dynamic skill 调取补上首版前审计：specialist 在真正执行 skill 前，先对“最终执行 skill + 最终 args”重新过 Harness policy；新增强约束 skill（如 `chatbi-file-ingestion`、`chatbi-auto-analysis`、`chatbi-comparison`、`chatbi-alias-manager`）的专线归属校验，并将拒绝原因优先收敛为“当前专线不应调取该 skill”，避免继续落到旧的 `skill_not_in_line` 兜底分支后才发现误路由 | `PYTHONPATH=. .venv/bin/python scripts/format_code.py backend/agent/harness_policy.py backend/agent/react_runner.py backend/agent/runner.py backend/agent/multi_agent_runner.py tests/test_react_runner.py`；`PYTHONPATH=. .venv/bin/python -m pytest tests/test_react_runner.py tests/test_multi_agent_runner.py tests/test_multi_agent_manager.py tests/test_harness_policy.py tests/test_run_tests_script.py -q` |
| 163  | 继续收紧后台心智负担：前端移除“多 Agents 管理”常规入口，并将审计页统一改为更产品化的“审计”；聊天页 admin trace 跳转也改到 `/audits`，同时保留 `/harness-audits` 与旧 `/multi-agents` 的兼容重定向，避免历史链接失效                                                                                                                                                                                                                | `cd frontend && npm run lint -- src/App.tsx src/components/AppLayout.tsx src/pages/ChatPage.tsx src/pages/HarnessAuditPage.tsx`                                                                                                                                                                                                                                                                                                               |
