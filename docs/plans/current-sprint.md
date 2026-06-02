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
| 上传                        | ✅ 完成     | 文件分析                                                                                              |
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
| G1   | 从旧双 MySQL / 双 schema 拓扑切回单 schema 时，旧 `database/mysql-data-log/` 和旧日志库不会自动迁移 | 如需保留旧日志，先导出旧 `chatbi_local_logs.log` 后导入 `chatbi_demo`；纯净演示可 `down -v` 后重建 |
| G3   | 在线 E2E 不进默认 CI，依赖 LLM / DB / 后端运行状态                                | 后端和 LLM 可用时跑 `python scripts/e2e_smoke.py --cases S1,S4,E1` 或按需全量                      |
| G4   | 上传文件复杂跨字段分析 / 风控建议仍偏轻量规则                                     | 如要增强，新增上传数据分析或风控建议 Skill，不复用演示库 decision-advisor                          |
| G5   | `docs/architecture/README.md` 等专题文档可能仍滞后于 guide / backend-architecture | 改动相关模块时顺手同步；主用户/技术文档在 `docs/guide/`，后端专题见 `docs/backend-architecture.md` |

## 最近变更

| 轮次 | 完成内容                                                                                                                                                 | 验证                                                                                                                                                                                      |
| ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 239  | 前端按钮与控件强调色从近黑色统一切换为 logo 主蓝 `#4788c8`：更新全局 `accent` token、主操作按钮、侧栏激活态、数据源卡片选中/悬浮/虚线边框、表单 focus / checkbox / 新增入口和 Debug 展开态 | `.venv/bin/python scripts/format_code.py frontend/src/index.css frontend/src/pages/ChatPage.tsx frontend/src/pages/HarnessAuditPage.tsx frontend/src/pages/DataSourcesPage.tsx frontend/src/pages/SkillAdminPage.tsx frontend/src/components/AppLayout.tsx frontend/src/components/HarnessDebugTimeline.tsx`；`npm run build`；`git diff --check` |
| 238  | 重做前端数据源接入页：恢复 `/data-sources` 路由与侧栏入口，支持 MySQL 连接新建/编辑/删除/测试/默认连接；对话页增加数据源选择，并按用户输入中的数据源名称、库名或连接串自动切换本轮 `db_connection_id`；修复保存连接注入 Skill 时仍查默认库的问题；数据库概览回答隐藏 `admin_*`、`app_*` 和日志等内部应用表，仅展示业务资产 | `npm run lint`；`npm run test -- dataSourceSwitch`；`npm run build`；`PYTHONPATH=. .venv/bin/python scripts/run_tests.py data-sources -- -q`；`PYTHONPATH=. .venv/bin/python scripts/run_tests.py foundation -- -q tests/test_connection_repo_db_overrides.py tests/test_run_tests_script.py` |
| 237  | `scripts/launch.sh` 启动前检测运行 env：当 `.env`、`.env.dev`、`.env.prod`、`env.dev` 均不存在时自动复制 `.env.example` 为 `.env`；移除脚本内 `source .env.prod`，避免 `CHATBI_SEED_USERS` 分号被 shell 当命令执行；补充 launch 脚本测试覆盖自动复制、已有 env 保留和分号 env 值 | `.venv/bin/python scripts/format_code.py scripts tests/test_launch_script.py`；`PYTHONPATH=. .venv/bin/python scripts/run_tests.py foundation -- -q tests/test_launch_script.py`；`bash scripts/launch.sh --help`；`git diff --check` |
| 236  | 支持通过 `CHATBI_SEED_USERS=username:password:role;...` 在后端启动时幂等写入多个 `app_user`，admin 也写入同一配置；移除旧 `CHATBI_DEFAULT_ADMIN_*` 入口；`.env.example`、`.env.dev`、`.env.prod` 与用户/架构文档同步说明 | `.venv/bin/python scripts/format_code.py backend tests`；`PYTHONPATH=. .venv/bin/python scripts/run_tests.py auth-memory -- -q`；`PYTHONPATH=. .venv/bin/python scripts/run_tests.py foundation -- -q`；`git diff --check` |
| 235  | `.env.example` 补充 LiteLLM 大模型配置占位，默认使用宿主机 Ollama 示例：`LLM_MODEL=ollama/qwen2.5:7b`、`API_BASE=http://host.docker.internal:11434`；README 同步说明 env 与管理页配置关系 | `git diff --check` |
