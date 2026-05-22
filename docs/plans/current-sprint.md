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
| 182  | 合并重复的测试自定义 agent：将原有 `test-case-generator.agent.md` 的细化测试流程吸收进 `testing-specialist.agent.md`，并删除旧文件，避免 GitHub 在线模式下出现两个职责高度重叠的测试 agent 选项 | 文档与配置自查：确认 `.github/agents/` 下仅保留一个测试 agent，且说明覆盖测试补充、注册、格式化、执行与失败诊断流程 |
| 181  | 为 GitHub 在线协作补齐仓库级 agent 配置：新增 `.github/copilot-instructions.md` 作为在线模式通用说明，并新增 `testing-specialist.agent.md`、`docs-specialist.agent.md` 两个仓库内自定义 agent，同时把入口写回 `AGENTS.md`，方便在 GitHub 上直接选择测试或文档专职 agent 执行任务 | 文档与配置自查：确认 `.github/agents/*.agent.md`、`.github/copilot-instructions.md`、`AGENTS.md` 路径与说明互相一致 |
| 180  | 继续调整审计页桌面端布局：将 Debug 时间线从审计结果内部彻底拆为右侧独立诊断卡片，与左侧“审计结果”卡同级并排、等高拉伸；同时给 Debug 卡增加淡蓝渐变底、强调边框和更像控制台的标题区，让它与普通白色信息卡形成明确区分 | `cd frontend && npm run lint -- src/pages/HarnessAuditPage.tsx src/components/HarnessDebugTimeline.tsx src/components/HarnessBusinessFlowCard.tsx` |
| 179  | 调整审计页信息架构：将“业务链路状态”和“Debug 时间线”改成桌面端左右两栏等宽布局，移动端自动回落单栏；同时把 Debug 开关升级为更高对比度的显眼按钮，默认直接显示事件总数，并将时间线抽成独立前端组件，便于继续扩展筛选与交互 | `cd frontend && npm run lint -- src/pages/HarnessAuditPage.tsx src/components/HarnessDebugTimeline.tsx src/components/HarnessBusinessFlowCard.tsx` |
| 178  | 修复经营建议专线绕过决策 Skill 的链路漏洞：多专线 `business_advisor` 现在会继承前置问数/结构化 rows 结果作为子代理初始状态，允许在已有 facts 的前提下合法调用 `chatbi-decision-advisor`；同时为 `finish` 增加专线级 Harness policy，禁止在未真正执行经营建议 Skill 前直接收尾，避免“被 policy 拒绝后改成手写建议文本”绕过内容审核与独立审计事件 | `PYTHONPATH=. .venv/bin/python scripts/format_code.py backend/agent/harness_state.py backend/agent/harness_policy.py backend/agent/react_runner.py backend/agent/runner.py backend/agent/multi_agent_runner.py tests/test_harness_policy.py tests/test_react_runner.py tests/test_multi_agent_runner.py`；`PYTHONPATH=. .venv/bin/python -m pytest tests/test_harness_policy.py tests/test_react_runner.py tests/test_multi_agent_runner.py tests/test_harness_audit.py tests/test_admin_harness_audit_route.py -q` |
| 177  | 修复审计页“最近 Trace”列表被无关单事件日志污染的问题：后端最近候选改为只保留真正进入聊天/agent 执行链路的 trace（`http.chat`、`agent.*`、`skill.*`），过滤 `sessions`、`dashboard.overview`、`admin.harness_audit` 等页面访问日志，方便直接定位最新聊天的审计记录 | `PYTHONPATH=. .venv/bin/python scripts/format_code.py backend/trace_repo.py tests/test_trace_repo.py scripts/run_tests.py`；`PYTHONPATH=. .venv/bin/python -m pytest tests/test_trace_repo.py tests/test_run_tests_script.py tests/test_admin_harness_audit_route.py tests/test_harness_audit.py -q` |
