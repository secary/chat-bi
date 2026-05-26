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
| 190  | 收束多 Agent 子专线内的重复 Skill 调用：在 `react_runner.py` 为 subagent ReAct 增加结果签名与参数签名检测，同一子 Agent 已有有效结果后，如果再次请求执行同一 Skill 且参数完全相同，会记录 `repeated_skill_converged` 并把已有结果交回路由层；不同参数的补查仍允许，避免 `demo_query` 在“问数+建议”复合需求里反复查询同一毛利结果 | `PYTHONPATH=. .venv/bin/python scripts/format_code.py backend/agent/react_runner.py tests/test_react_runner.py`；`PYTHONPATH=. .venv/bin/python -m pytest tests/test_react_runner.py tests/test_multi_agent_runner.py tests/test_harness_audit.py -q`；`PYTHONPATH=. .venv/bin/python -m pytest tests/test_multi_agent_intent.py tests/test_multi_agent_manager.py tests/test_run_tests_script.py tests/test_admin_harness_audit_route.py -q` |
| 189  | 将多 Agent 收束为受 Harness 审计的多路由迁移：新增 `multi_agent_intent.py` 作为受控意图识别层，将 `query_then_decide`、`query_then_viz`、`query_then_decide_then_viz` 等复合需求先转成 `required_routes`，再由 Harness 生成首轮与后续路由，减少对 Manager 自由 `tasks` 规划的依赖；经营建议产出后记录 `route_objective_completed` 并直接进入汇总，避免“建议已完成还回 Manager 空确认”的链路漂移 | `PYTHONPATH=. .venv/bin/python scripts/format_code.py backend/agent/multi_agent_intent.py backend/agent/multi_agent_runner.py tests/test_multi_agent_intent.py tests/test_multi_agent_runner.py scripts/run_tests.py`；`PYTHONPATH=. .venv/bin/python -m pytest tests/test_multi_agent_intent.py tests/test_multi_agent_runner.py tests/test_multi_agent_manager.py tests/test_harness_audit.py tests/test_admin_harness_audit_route.py tests/test_run_tests_script.py -q` |
| 188  | 降低 Dependabot 噪音：将 `.github/dependabot.yml` 中 Python、frontend npm、GitHub Actions、Docker 的版本更新频率从按周改为按月，并将每类 `open-pull-requests-limit` 收紧到 1，避免首次启用后持续堆积多条并行更新 PR | 配置自查：确认 4 类生态均已切换为 `monthly`，且 `open-pull-requests-limit` 均为 1；确认 `AGENTS.md` 已同步说明当前低频策略 |
| 187  | 修复 Python 供应链审计命中的已知漏洞依赖：将 `cryptography`、`starlette`、`pillow`、`pypdf`、`pytest`、`weasyprint` 升到 `pip-audit` 报告给出的安全版本区间，并同步刷新 `uv.lock`；其中 `starlette` 作为 `fastapi` 传递依赖改为显式 pin 到 `1.0.1`，避免继续解析到存在漏洞的 `1.0.0` | `PYTHONPATH=. .venv/bin/python scripts/run_tests.py foundation -- -q`；`PYTHONPATH=. .venv/bin/python -m pytest tests/test_report_pdf.py tests/test_admin_multi_agents.py tests/test_admin_harness_audit_route.py -q` |
| 186  | 将 PR 供应链检查从 GitHub `dependency-review-action` 切换为更适配当前 `uv` 仓库的方案：删除 `.github/dependency-review-config.yml`，并将 `dependency-review.yml` 改为 `Supply Chain Audit`，其中 Python 走 `uv export --frozen` + `pip-audit`，前端走 `npm audit --audit-level=high`，避免公开仓库已开启 dependency graph 但 `uv.lock` 仍无法被官方 dependency review 正常识别时持续误报红 | 配置自查：确认 workflow 不再依赖 `actions/dependency-review-action`；确认 Python 审计基于 `uv.lock` 导出锁定依赖，前端审计基于 `package-lock.json` 与 `npm audit` |
