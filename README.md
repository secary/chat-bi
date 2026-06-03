# 零眸智能 ChatBI

面向银行场景的对话式数据分析 Demo。用户可以用中文自然语言完成问数、趋势分析、经营建议、文件上传分析和多 Agent 协作；系统通过 FastAPI + LiteLLM 编排 Skill 脚本，再把结果以 SSE 流式返回到 React 前端。

## 项目现状

- 已支持：中文问数、图表与 KPI、文件上传分析、会话管理、审计页、Skill 管理、LLM 配置、用户管理、多 Agent 编排。
- 当前前端主入口：`/` 对话页，`/audits` 审计页，`/skills` 技能接入，`/llm` LLM 配置，`/users` 用户管理。
- 已下线：独立仪表盘页面、前端数据源管理页面、会话 PDF 导出。
- 后端仍保留部分扩展能力：如数据源连接管理接口，可作为后续多库能力基础。

## 技术栈

| 层 | 技术 |
| --- | --- |
| 前端 | React 19 + TypeScript + Vite + Tailwind CSS + ECharts 6 |
| 后端 | FastAPI + Python 3.11+ + LiteLLM |
| 数据库 | MySQL 8.0 |
| 协议 | SSE 流式输出 |
| 质量 | ruff + black + ESLint |

## 核心能力

- 中文自然语言问数，基于语义层和受控 SQL 做只读查询
- 分类对比、时间趋势、KPI 卡片和 ECharts 图表渲染
- 上传 CSV/XLSX 后做结构识别、预览、指标提案和采纳看板
- 多会话、会话记忆、生成中止、链路 trace 审计
- 多 Agent / 多专线协同，支持上传分析、问数、环比、可视化、别名维护、经营建议
- 管理端支持 Skill 开关、LLM Profile 配置、用户管理

## 快速开始

### 1. 生产式本地运行

```bash
cp .env.example .env
bash scripts/launch.sh
```

访问地址：

- 应用：`http://localhost:5173`（前端静态资源 + 同源 `/api`）
- MySQL：`127.0.0.1:3307`（`chatbi_demo` 包含业务、应用、管理与日志表）

启动用户会在后端启动时按 `.env` 自动写入 `app_user`；把管理员也放在同一个配置里：

```dotenv
CHATBI_SEED_USERS=admin:admin123:admin;demo:demo123:user;analyst:analyst123:user
```

生产式本地使用一体镜像 `chatbi-app`：容器内同时运行 nginx 和 FastAPI，nginx 通过同源 `/api` 反代到本容器内的后端进程。
如需只启动不打开浏览器，可运行 `bash scripts/launch.sh --no-open`；如需跳过重建镜像，可加 `--no-build`。

### 2. 开发热更新

首次进入仓库建议先同步依赖：

```bash
bash scripts/bootstrap_dev.sh --sync
```

开发态启动：

```bash
bash scripts/start_dev.sh
```

访问地址：

- 前端：`http://localhost:5173`
- 后端：`http://localhost:8000`
- MySQL：`127.0.0.1:33067`（`chatbi_demo` 包含业务、应用、管理与日志表）

开发态只保留 MySQL 容器 `chatbi-db-dev`；FastAPI reload server 和 Vite dev server 都运行在宿主机，调试和热更新更直接。

本机开发脚本默认关闭登录：

- 后端：`CHATBI_AUTH_ENABLED=false`
- 前端：`VITE_AUTH_ENABLED=false`

如需与生产一致的登录流程，请在 `.env.dev` 中同步开启这两个开关。

只启动开发数据库：

```bash
bash scripts/start_dev.sh --db-only
```

如需拆开手动启动前后端，先运行上面的 `--db-only`，再分别执行：

```bash
PYTHONPATH=. .venv/bin/python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
cd frontend && VITE_PROXY_TARGET=http://127.0.0.1:8000 VITE_AUTH_ENABLED=false npm run dev
```

## 常用命令

```bash
# 日常进场
bash scripts/bootstrap_dev.sh

# 首次/依赖变动
bash scripts/bootstrap_dev.sh --sync

# 开发启动（MySQL in Docker，前后端 on host）
bash scripts/start_dev.sh

# 代码格式化
bash scripts/bootstrap_dev.sh --format

# 快速测试
PYTHONPATH=. .venv/bin/python scripts/run_tests.py foundation -- -q

# 在线冒烟（需 DB + 后端 + LLM 可用）
PYTHONPATH=. .venv/bin/python scripts/e2e_smoke.py --cases S1,S4,E1
```

## 系统怎么工作

```text
用户输入 / 上传文件
  -> React 前端
  -> POST /chat 或 POST /upload
  -> FastAPI 路由层
  -> Agent Runner / ReAct Runner / Multi-Agent Manager
  -> 读取 skills/*/SKILL.md 选择 Skill
  -> 执行 skills/*/scripts 确定性脚本
  -> SkillResult -> formatter / renderers
  -> SSE 输出 thinking / text / chart / kpi_cards / proposal
  -> 前端消息流渲染与会话落库
```

关键后端入口：

- `backend/main.py`：FastAPI 应用与路由注册
- `backend/routes/chat_route.py`：`/chat` SSE 与 `/abort`
- `backend/routes/sessions_route.py`：会话列表、消息读取、重命名、删除
- `backend/agent/runner.py`：Legacy / ReAct 主编排
- `backend/agent/multi_agent_*`：多专线调度与汇总
- `backend/agent/prompt_builder.py`：扫描 `skills/*/SKILL.md`

## Skills 概览

当前仓库主要 Skill 包括：

- `chatbi-semantic-query`：自然语言问数
- `chatbi-semantic-processing`：语义预处理与意图辅助
- `chatbi-comparison`：环比 / 时间对比
- `chatbi-metric-explainer`：指标口径解释
- `chatbi-alias-manager`：别名维护
- `chatbi-decision-advisor`：经营建议
- `chatbi-chart-recommendation`：图表推荐
- `chatbi-dashboard-orchestration`：看板编排中间件
- `chatbi-database-overview`：库表概览
- `chatbi-file-ingestion`：文件读取与预处理
- `chatbi-auto-analysis`：上传数据指标提案与采纳执行

每个 Skill 的触发条件、不要用场景和命令示例都在 `skills/<skill-name>/SKILL.md`。

## 目录结构

```text
chat-bi/
├── AGENTS.md
├── README.md
├── TODO.md
├── Dockerfile
├── docker-compose.yml
├── docker-compose.dev.yml
├── docker-compose.prod.yml
├── pyproject.toml
├── deploy/
│   ├── docker-entrypoint.dev.sh
│   ├── docker-entrypoint.prod.sh
│   └── nginx.app.conf
├── scripts/
│   ├── bootstrap_dev.sh
│   ├── run_tests.py
│   ├── format_code.py
│   └── e2e_smoke.py
├── database/
│   └── init.sql
├── backend/
│   ├── main.py
│   ├── routes/
│   ├── agent/
│   ├── renderers/
│   ├── session_repo.py
│   ├── memory_service.py
│   └── trace*.py
├── frontend/
│   └── src/
│       ├── pages/
│       ├── components/
│       ├── hooks/
│       ├── api/
│       └── contexts/
├── skills/
│   ├── _agents/
│   ├── _shared/
│   └── chatbi-*/SKILL.md + scripts/
├── docs/
└── tests/
```

## 数据库与环境变量

默认数据库职责：

- `chatbi_demo`：业务数据、语义层、应用表 `app_*`、管理表 `admin_*`、链路日志表 `log`

最常用环境变量：

| 变量 | 说明 |
| --- | --- |
| `CHATBI_DB_HOST/PORT/NAME/USER/PASSWORD` | 业务库连接 |
| `CHATBI_LOG_DB_NAME` | 可选日志库名；默认复用 `CHATBI_DB_NAME` |
| `LLM_MODEL/API_BASE/OPENAI_API_KEY` | LiteLLM 模型配置；`.env.example` 默认用本地 Ollama 占位 |
| `CHATBI_AGENT_REACT` | `1` 启用 ReAct，多轮 Skill 调度 |
| `CHATBI_AGENT_MAX_STEPS` | 单轮消息最大 Agent 步数 |
| `CHATBI_AUTH_ENABLED` | 是否开启登录 |
| `CHATBI_MEMORY_DISABLED` | 是否关闭记忆 |
| `CHATBI_JWT_SECRET` | JWT 密钥 |
| `CHATBI_SEED_USERS` | 启动时写入 `app_user`，格式 `username:password:role;...`，建议包含至少一个 `admin` |

完整示例见 [`.env.example`](.env.example)。

LLM 配置可通过 `.env` 提供启动占位，也可在管理页维护；运行时以管理页激活的 Profile 优先。

## 测试

测试入口统一走 `scripts/run_tests.py`，已按模块分组：

- `foundation`
- `skills`
- `agent`
- `admin`
- `auth-memory`
- `dashboard`
- `data-sources`
- `upload`

示例：

```bash
PYTHONPATH=. .venv/bin/python scripts/run_tests.py foundation -- -q
PYTHONPATH=. .venv/bin/python scripts/run_tests.py agent -- -q
```

前端检查：

```bash
cd frontend
npm run lint
npm run build
```

## 常见问题

### MySQL 初始化后登录报错或缺表

MySQL 官方镜像只会在空数据目录时执行初始化 SQL。若你沿用了旧 volume 或旧目录，新表不会自动补上。

处理方式：

```bash
docker compose down -v
bash scripts/launch.sh
```

开发数据库重建：

```bash
docker compose --env-file .env.dev -f docker-compose.dev.yml down -v
bash scripts/start_dev.sh --db-only
```

### 修改 `database/init.sql` 后数据没变化

这是正常的。初始化 SQL 不会自动重放，需要清空对应 MySQL 数据卷后再启动。

### 上传文件为什么没走演示库问数

上传文件链路优先使用 `chatbi-file-ingestion`，必要时再进入 `chatbi-auto-analysis`。只有明确是演示库问数，才会走 `chatbi-semantic-query`。

## 文档导航

| 主题 | 路径 |
| --- | --- |
| Agent 协作规则 | [AGENTS.md](AGENTS.md) |
| 当前迭代事实源 | [docs/plans/current-sprint.md](docs/plans/current-sprint.md) |
| 架构总览 | [docs/architecture/README.md](docs/architecture/README.md) |
| 技术实现指南 | [docs/guide/tech-guide.md](docs/guide/tech-guide.md) |
| 使用指南 | [docs/guide/user-guide.md](docs/guide/user-guide.md) |
| 测试说明 | [docs/testing/README.md](docs/testing/README.md) |
| CI / CD | [docs/ci-cd/README.md](docs/ci-cd/README.md) |

## 备注

- 本仓库当前以 Demo / 内部验证为主，默认数据与规则面向演示业务场景。
- 如果后续要做多数据库接入，建议优先走“自然语言触发接库 + Skill 确定性校验”的方向，而不是恢复旧式手填页面。
