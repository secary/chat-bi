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
| 194  | 将多专线聊天体验改为用户无感：多 Agent 运行时不再向前端转发子执行线 thinking，最终 `stream_result_events(..., include_thinking=False)` 会抑制 `plan_trace` / `plan_summary` 的 SQL 与识别过程展示；保留后台 Harness 日志和审计页用于排查 | `PYTHONPATH=. .venv/bin/python scripts/format_code.py backend/agent/formatter.py backend/agent/multi_agent_runner.py tests/test_agent_skill_protocol.py tests/test_multi_agent_runner.py`；`PYTHONPATH=. .venv/bin/python -m pytest tests/test_agent_skill_protocol.py tests/test_multi_agent_runner.py tests/test_multi_agent_summarize.py -q`；`PYTHONPATH=. .venv/bin/python scripts/run_tests.py agent -- -q` |
| 193  | 修复最终回答正文泄露内部执行线信息：`multi_agent_summarize.py` 汇总输入不再传 `agent`、`label`、`handoff_instruction`，只传用户问题与纯 observation 结果块；汇总 prompt 明确禁止输出执行线 / agent / skill / Observation 等内部链路字段，避免正文出现“查询专线：B线（demo_query）” | `PYTHONPATH=. .venv/bin/python scripts/format_code.py backend/agent/multi_agent_summarize.py tests/test_multi_agent_summarize.py scripts/run_tests.py`；`PYTHONPATH=. .venv/bin/python -m pytest tests/test_multi_agent_summarize.py tests/test_multi_agent_runner.py tests/test_run_tests_script.py -q` |
| 192  | 优化多专线前端可见命名：registry 默认 `label` 从业务意图名改为 A线 / B线 / C线 / D线 / E线 / F线，保留内部 agent id 与 role_prompt 不变；聊天 SSE 不再展示调度 / 汇总编排层文案，只展示执行线代号与子任务自身进度；后台多 Agents 管理页同步弱化 Manager 规划表述 | `PYTHONPATH=. .venv/bin/python scripts/format_code.py backend/agent/multi_agent_runner.py tests/test_multi_agent_runner.py`；`PYTHONPATH=. .venv/bin/python -m pytest tests/test_multi_agent_runner.py tests/test_admin_multi_agents.py -q`；`cd frontend && npm run lint` |
| 191  | 完成“Manager 退化成意图识别器”阶段收口：多 Agent 入口不再调用 Manager LLM 自由产出 `tasks[]`，所有已识别单路由 / 多路由意图均由 `multi_agent_intent.py` 输出 `current_route` + `route_sequence`，再由 Harness 内部生成和审计任务；未命中受控意图时直接降级单 Agent；同步将运行态提示从 Manager 规划改为 Harness 路由 / 汇总，并补充图表建议误入经营建议专线的分类边界测试 | `PYTHONPATH=. .venv/bin/python scripts/format_code.py backend/agent/multi_agent_intent.py backend/agent/multi_agent_runner.py backend/agent/multi_agent_manager.py tests/test_multi_agent_intent.py tests/test_multi_agent_runner.py`；`PYTHONPATH=. .venv/bin/python -m pytest tests/test_multi_agent_intent.py tests/test_multi_agent_runner.py tests/test_multi_agent_manager.py tests/test_run_tests_script.py -q`；`PYTHONPATH=. .venv/bin/python -m pytest tests/test_harness_audit.py tests/test_admin_harness_audit_route.py tests/test_multi_agent_manager.py -q`；`PYTHONPATH=. .venv/bin/python scripts/run_tests.py agent -- -q` |
| 190  | 收束多 Agent 子专线内的重复 Skill 调用：在 `react_runner.py` 为 subagent ReAct 增加结果签名与参数签名检测，同一子 Agent 已有有效结果后，如果再次请求执行同一 Skill 且参数完全相同，会记录 `repeated_skill_converged` 并把已有结果交回路由层；不同参数的补查仍允许，避免 `demo_query` 在“问数+建议”复合需求里反复查询同一毛利结果 | `PYTHONPATH=. .venv/bin/python scripts/format_code.py backend/agent/react_runner.py tests/test_react_runner.py`；`PYTHONPATH=. .venv/bin/python -m pytest tests/test_react_runner.py tests/test_multi_agent_runner.py tests/test_harness_audit.py -q`；`PYTHONPATH=. .venv/bin/python -m pytest tests/test_multi_agent_intent.py tests/test_multi_agent_manager.py tests/test_run_tests_script.py tests/test_admin_harness_audit_route.py -q` |
