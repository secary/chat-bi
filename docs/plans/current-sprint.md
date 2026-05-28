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
| 上传 / PDF                  | ✅ 完成     | 文件分析、PDF 降级导出                                                                                |
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

| 编号 | Gap                                                                               | 下一步                                                                                             |
| ---- | --------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| G1   | 首次切到双实例拓扑时，旧 named volume / 宿主机目录不会自动迁移或重放初始化 SQL    | 如需拿到纯净演示库与纯日志库，执行对应 compose 的 `down -v` 后再重新 `up -d --build`               |
| G3   | 在线 E2E 不进默认 CI，依赖 LLM / DB / 后端运行状态                                | 后端和 LLM 可用时跑 `python scripts/e2e_smoke.py --cases S1,S4,E1` 或按需全量                      |
| G4   | 上传文件复杂跨字段分析 / 风控建议仍偏轻量规则                                     | 如要增强，新增上传数据分析或风控建议 Skill，不复用演示库 decision-advisor                          |
| G5   | `docs/architecture/README.md` 等专题文档可能仍滞后于 guide / backend-architecture | 改动相关模块时顺手同步；主用户/技术文档在 `docs/guide/`，后端专题见 `docs/backend-architecture.md` |

## 最近变更

| 轮次 | 完成内容                                                                                                                                                 | 验证                                                                                                                                                                                      |
| ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 218  | 将审计页与技能接入页收敛到聊天工作台 UI 风格：采用聊天输入区式软阴影工具栏、圆润白色面板、浅色高光列表项，并弱化审计 Debug 时间线的强装饰样式          | `PYTHONPATH=. .venv/bin/python scripts/format_code.py frontend/src/pages/HarnessAuditPage.tsx frontend/src/pages/SkillAdminPage.tsx frontend/src/components/HarnessDebugTimeline.tsx frontend/src/components/HarnessBusinessFlowCard.tsx`；`cd frontend && npm run lint`；`cd frontend && npm run build` |
| 217  | LLM 配置页厂商选择新增“其他”选项；选中后需手动填写模型与 Base URL，再配合 API Key 测试并启用                                                            | `PYTHONPATH=. .venv/bin/python scripts/format_code.py frontend/src/pages/LlmConfigPage.tsx`；`cd frontend && npm run lint`；`cd frontend && npm run build`                               |
| 216  | LLM 配置页已保存模型卡片补充模型参数展示，备注名、状态、测试/删除操作与真实模型名分层呈现                                                               | `PYTHONPATH=. .venv/bin/python scripts/format_code.py frontend/src/pages/LlmConfigPage.tsx`；`cd frontend && npm run lint`；`cd frontend && npm run build`                               |
| 215  | LLM 配置页已保存模型卡片新增删除操作；删除前确认，删除中禁用操作，当前配置且唯一模型时禁止删除并提示                                                    | `PYTHONPATH=. .venv/bin/python scripts/format_code.py frontend/src/pages/LlmConfigPage.tsx`；`cd frontend && npm run lint`；`cd frontend && npm run build`                               |
| 214  | 调整 LLM 配置页当前配置卡片：移除“来源”展示，改为直接显示当前生效模型名，避免只看到备注名无法确认实际模型                                                | `PYTHONPATH=. .venv/bin/python scripts/format_code.py frontend/src/pages/LlmConfigPage.tsx`；`cd frontend && npm run lint`；`cd frontend && npm run build`                               |
