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
| 212  | 将 dev Docker 源切换改为 `.env.dev` 变量控制：默认 fallback 仍为官方源，本机可通过镜像与包源变量切到国内源，不需要额外 compose override 文件             | `docker compose --env-file .env.dev -f docker-compose.dev.yml config`；`docker compose --env-file .env.dev -f docker-compose.dev.yml build backend frontend`                              |
| 211  | 明确浏览器 tab 品牌：入口 HTML 继续使用紫色闪电 `favicon.svg` 与“零眸智能 ChatBI”标题，并增加 `shortcut icon` 与版本参数避免旧 favicon 缓存              | `PYTHONPATH=. .venv/bin/python scripts/format_code.py frontend/index.html`；`cd frontend && npm run lint`                                                                                 |
| 210  | 从 `logo/零眸logo.ai` 提取前端可用品牌资源，新增侧栏零眸视觉标识，并以图标 + 品牌名组合替换纯文字标题                                                    | `PYTHONPATH=. .venv/bin/python scripts/format_code.py frontend/src/components/AppLayout.tsx`；`cd frontend && npm run lint`                                                               |
| 209  | 精简聊天页导航结构：移除左侧二级会话侧栏，将“新对话”移到聊天页顶部工具区；主侧栏同步收窄并改为更轻的单层工作台导航样式，减少空态工作台和聊天区的视觉割裂 | `PYTHONPATH=. .venv/bin/python scripts/format_code.py frontend/src/pages/ChatPage.tsx frontend/src/hooks/useChat.ts frontend/src/components/AppLayout.tsx`；`cd frontend && npm run lint` |
| 208  | 将聊天空态首屏改为类工作台入口：大标题 + 大号输入框 + 能力卡片 + 最近会话列表；消息后的底部输入区保持紧凑样式，避免影响常规对话流                        | `cd frontend && npm run lint`                                                                                                                                                             |
