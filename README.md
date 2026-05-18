# 零眸智能 ChatBI

面向银行业务场景的对话式数据分析 Demo。用中文自然语言完成问数、环比分析、指标解释、经营决策建议、语义别名维护和文件导入，支持多会话管理与多步 Skill 链式执行。

## 快速开始（Docker 全栈）

生产式本地运行会构建前端静态产物，并由 nginx 提供页面：

```bash
# 1. 复制环境变量模板，填入 LLM API Key
cp .env.example .env

# 2. 启动所有服务
docker compose up -d --build

# 3. 浏览器访问（macOS/Linux）
open http://localhost:5173
# Windows：start http://localhost:5173
```

前端通过 **同源路径 `/api`** 访问后端（nginx 反代到容器 `backend`），避免浏览器跨端口 CORS。`docker-compose.yml` 构建参数已**固定为 `/api`**，不再读取根目录 `.env` 里的 `FRONTEND_API_BASE_URL`，避免旧配置写成 `http://localhost:8000` 导致打包后仍直连 8000。单独构建前端镜像时可用 `--build-arg VITE_API_BASE_URL=...` 覆盖。

服务端口：

| 服务 | 宿主机端口 |
|------|-----------|
| frontend | 5173 |
| backend | 8000 |
| MySQL | 3307 |

容器名前缀为 `chatbi-prod-*`，项目名为 `chatbi-prod`。

### 默认登录（前端）

数据库按 `database/init.sql` **首次初始化**后，内置管理员账号如下（用于登录 Web 后的对话、仪表盘等）：

| 字段 | 值 |
|------|-----|
| 用户名 | `admin` |
| 密码 | `admin123` |

对外或生产部署前请修改密码，并通过「用户管理」创建业务账号。

### Docker：登录报 500（Internal Server Error）

常见原因是 **MySQL 数据目录来自旧版本**：官方镜像只在**空数据目录**时执行一次 `database/init.sql`。若 `./database/mysql-data` 早已存在，升级仓库里的 `init.sql` 后也不会自动补表，可能导致缺少 `chatbi_app_user` / `chatbi_admin_llm_settings` 等前缀表，登录时后端会报表不存在或权限类错误（容器日志里可见 `pymysql.err.OperationalError`）。

**处理（会清空该环境 MySQL 中的演示数据，请先备份需要保留的内容）：**

```bash
docker compose down
# Windows PowerShell：Remove-Item -Recurse -Force .\database\mysql-data
# 或手动删除/重命名项目下的 database/mysql-data 目录
docker compose up -d
```

重新拉起后，确认容器内 `chatbi_demo` 含 `chatbi_app_user`，且 `chatbi_local_logs` 含 `chatbi_logs_trace_log` 后再登录 `admin` / `admin123`。

## 本地开发启动

首次拉代码后，建议先执行一次：

```bash
bash scripts/bootstrap_dev.sh --sync
```

它会为当前仓库配置 Git `pre-commit` hook，并用 `uv sync` / `npm ci` 同步 Python 与前端依赖。日常进场可只运行 `bash scripts/bootstrap_dev.sh` 做轻量检查；需要本地清理时运行 `bash scripts/bootstrap_dev.sh --format`。

### 方式 A：Docker 热更新

推荐日常开发使用，前后端源码会挂载进容器：

```bash
docker compose --env-file .env.dev -f docker-compose.dev.yml up -d --build

# 浏览器访问（macOS/Linux）
open http://localhost:5174
# Windows：start http://localhost:5174
```

开发环境端口：

| 服务 | 宿主机端口 |
|------|-----------|
| frontend | 5174 |
| backend | 8001 |
| MySQL | 3308 |

- 修改 `backend/` 或 `skills/`：后端自动 reload，无需重建镜像。
- 修改 `frontend/`：Vite 自动热更新，无需重建镜像。
- 修改 `frontend/package.json` 或 `package-lock.json`：重启 frontend 容器即可（入口脚本会对比 lock 并自动 `npm ci`）；若仍缺包可执行 `docker compose --env-file .env.dev -f docker-compose.dev.yml down -v` 后重新 `up --build` 清空 `frontend-node-modules` 卷。
- 修改 Dockerfile 或系统依赖：需要重新 `--build`。
- 修改 `database/init.sql`：已有 `database/mysql-data-dev/` 不会自动重放，需重置开发数据目录后再启动。
- 容器名前缀为 `chatbi-dev-*`，可以和生产式本地运行并存。

### 方式 B：宿主机启动前后端

```bash
# Backend
uv sync
source .venv/bin/activate
uvicorn backend.main:app --reload --port 8000

# Frontend（另开终端）
cd frontend && npm ci && npm run dev
```

MySQL 仍需 Docker：

```bash
docker compose up -d demo-mysql
```

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | React 19 + TypeScript + Vite + Tailwind CSS + ECharts 6 |
| 后端 | FastAPI + Python 3.11+ + LiteLLM |
| 数据库 | MySQL 8.0（Docker） |
| 流式 | Server-Sent Events（SSE） |
| 质量 | ruff + ESLint（`scripts/format_code.py` 另含 black） |

## 项目结构

```
chat-bi/
├── AGENTS.md、CLAUDE.md             # Agent 规则入口
├── .env.example、docker-compose*.yml
├── scripts/
│   ├── bootstrap_dev.sh             # 进场 / --sync / --format
│   ├── run_tests.py                 # 分套件 pytest（foundation、agent、skills…）
│   ├── format_code.py、 e2e_smoke.py
├── database/init.sql、migrations/
├── backend/
│   ├── main.py                      # FastAPI：/chat SSE、/upload、/abort
│   ├── routes/                      # auth、sessions、chat、dashboard、admin/*
│   ├── agent/                       # runner、react_runner、multi_agent_*、
│   │                                # prompt_builder、context_window、abort_*、…
│   ├── memory_*、session_repo、vision/、report/、renderers/
├── frontend/src/                     # pages（Chat、Dashboard、Admin…）、
│                                    # api/client.ts、hooks/useChat.ts、components/
├── skills/
│   ├── _agents/registry.yaml        # 多专线 registry
│   ├── _shared/、chatbi-*/SKILL.md + scripts/
└── tests/                           # 见 scripts/run_tests.py MODULE_SUITES
```

## 测试

```bash
# macOS/Linux
PYTHONPATH=. .venv/bin/python scripts/run_tests.py foundation -- -q

# Windows
PYTHONPATH=. .venv\Scripts\python.exe scripts/run_tests.py foundation -- -q
```

在线冒烟（需 DB + 后端 + LLM）：`python scripts/e2e_smoke.py --cases S1,S4,E1`

## 架构流程

```
用户输入（文字 / 文件）
  → React（X-Trace-Id、session_id；生成中可 POST /abort）
  ┌─ POST /upload → /tmp/chatbi-uploads/…
  └─ POST /chat（SSE）
       → chat_route → stream_chat
           ├─ multi_agents → Manager 多轮规划 → 各专线 stream_specialist
           ├─ CHATBI_AGENT_REACT 开启 → react_runner（context_window + 多轮 call_skill）
           └─ 否则 Legacy 单次 plan（可选 query → decision-advisor 双步链）
           → prompt_builder（Skill 元数据 + 记忆 + 专线 role）
           → executor 子进程 skills/*/scripts → SkillResult
           → formatter / renderers → SSE（thinking / text / chart / kpi_cards /
              analysis_proposal / dashboard_ready / error）
       → 消息落库；BackgroundTasks 刷新记忆
       → trace → chatbi_local_logs（compose 下与 chatbi_demo 同 MySQL 实例）
  → 前端 MessageBubble（Markdown/KaTeX、提案卡片、采纳看板）
```

上传路径优先 **file-ingestion → auto-analysis**（指标提案 / 采纳看板），勿用 semantic-query 查演示库代替用户文件。

## Skills

| Skill | 功能 |
|-------|------|
| `chatbi-semantic-query` | 将自然语言转换为 SQL，查询 `chatbi_demo` 并返回表格与图表 |
| `chatbi-semantic-processing` | 语义预处理、意图识别与查询辅助 |
| `chatbi-alias-manager` | 维护 `alias_mapping`，将业务别名映射到标准字段名 |
| `chatbi-decision-advisor` | 先计算指标事实，再按确定性规则生成经营决策建议 |
| `chatbi-metric-explainer` | 解释指标口径、来源与使用场景 |
| `chatbi-comparison` | 环比分析：支持最近两月对比、全年月度趋势、季度汇总三种模式 |
| `chatbi-chart-recommendation` | 根据查询结果推荐图表类型和 ECharts 配置方向 |
| `chatbi-dashboard-orchestration` | 编排仪表盘视图所需的指标、图表与摘要 |
| `chatbi-database-overview` | 输出数据库表、字段和样例数据概览 |
| `chatbi-file-ingestion` | 读取 CSV/XLSX，识别表头、校验类型并返回预览 JSON |
| `chatbi-auto-analysis` | 上传表指标提案、用户采纳后确定性计算与看板中间件 |

每个 Skill 的触发条件、工作流和安全边界见 `skills/<skill-name>/SKILL.md`。选用依赖 Prompt 元数据与各专线边界，**无执行前硬校验**。

## 环境变量

关键变量见 `.env.example`：

| 变量 | 说明 |
|------|------|
| `LLM_MODEL` | LiteLLM 模型名（如 `gpt-4o-mini`、`MiniMax-M2.7`） |
| `OPENAI_API_KEY` | LLM API Key |
| `API_BASE` | LLM API Base URL（可选，OpenAI-compatible 代理用） |
| `CHATBI_DB_HOST` | 业务库主机（容器内默认 `demo-mysql`） |
| `CHATBI_DB_PORT` | 业务库端口（容器内默认 `3306`） |
| `CHATBI_DB_USER` | 业务库用户（默认 `demo_user`） |
| `CHATBI_DB_PASSWORD` | 业务库密码（默认 `demo_pass`） |
| `CHATBI_DB_NAME` | 业务库库名（默认 `chatbi_demo`） |
| `CHATBI_APP_DB_HOST/PORT/USER/PASSWORD/NAME` | 可选；前端用户与会话表默认沿用 `CHATBI_DB_*` |
| `CHATBI_ADMIN_DB_HOST/PORT/USER/PASSWORD/NAME` | 可选；配置与技能开关表默认沿用 `CHATBI_DB_*` |
| `CHATBI_LOG_DB_HOST` | 日志库主机（未配置时回退到业务库） |
| `CHATBI_LOG_DB_PORT` | 日志库端口 |
| `CHATBI_LOG_DB_USER` | 日志库用户 |
| `CHATBI_LOG_DB_PASSWORD` | 日志库密码 |
| `CHATBI_LOG_DB_NAME` | 日志库库名（默认 `chatbi_local_logs`） |
| `CHATBI_AGENT_REACT` | `1` 开启 ReAct（默认）；`0`/`false` 走 Legacy |
| `CHATBI_AGENT_MAX_STEPS` | ReAct 每轮用户消息最大 LLM 步数（默认 `8`） |
| `CHATBI_AUTH_ENABLED` | 用户登录；dev compose 默认 `false` |
| `CHATBI_MEMORY_DISABLED` | `1` 关闭记忆读写与 prompt 注入 |
| `CHATBI_JWT_SECRET` | JWT 密钥（生产务必修改） |
| `FRONTEND_API_BASE_URL` | 可选备忘。生产 compose 前端构建已固定 `/api` |

默认数据库职责：

- `chatbi_demo`：演示业务数据、语义层、应用表 `chatbi_app_*`、管理表 `chatbi_admin_*`
- `chatbi_local_logs`：链路日志 `chatbi_logs_trace_log`

**Docker compose** 中 `demo-mysql` 同时承载上述两个 database（`CHATBI_LOG_DB_HOST=demo-mysql`）。宿主机 `.env` 若设 `CHATBI_LOG_DB_PORT=33067` 表示连接独立日志实例，非 compose 默认。

如需主动拆分应用库或管理库，可显式设置 `CHATBI_APP_DB_*` / `CHATBI_ADMIN_DB_*`。

环境文件建议：

| 环境 | env 文件 | Compose |
|------|----------|---------|
| 生产式本地 / 测试 | `.env` | `docker-compose.yml` |
| 开发热更新 | `.env.dev`（本地，Git 忽略） | `docker-compose.dev.yml` |

## 开发文档

| 主题 | 路径 |
|------|------|
| Agent 规则与工作方式 | [AGENTS.md](AGENTS.md) |
| 技术与使用指南（功能与页面） | [docs/guide/user-guide.md](docs/guide/user-guide.md) |
| 技术实现指南（Agent / Prompt / 记忆 / Skill） | [docs/guide/tech-guide.md](docs/guide/tech-guide.md) |
| 系统架构与模块边界 | [docs/architecture/README.md](docs/architecture/README.md) |
| 编码规范 | [docs/conventions/README.md](docs/conventions/README.md) |
| 测试与 CI | [docs/testing/README.md](docs/testing/README.md)、[docs/ci-cd/README.md](docs/ci-cd/README.md) |
| 当前迭代任务 | [docs/plans/current-sprint.md](docs/plans/current-sprint.md) |
| Skill 能力说明 | `skills/<skill-name>/SKILL.md` |
