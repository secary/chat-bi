# 零眸智能 ChatBI

面向银行业务场景的对话式数据分析 Demo，让用户用中文自然语言完成问数、文件导入、语义别名维护和经营决策建议生成。

## 快速开始（Docker 全栈）

生产式本地运行会构建前端静态产物，并由 nginx 提供页面：

```bash
# 1. 复制环境变量模板，填入 LLM API Key
cp .env.example .env

# 2. 启动所有服务
docker compose up -d --build

# 3. 浏览器访问
open http://localhost:5173
```

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

## 本地开发启动

### 方式 A：Docker 热更新

推荐日常开发使用，前后端源码会挂载进容器：

```bash
docker compose --env-file .env.dev -f docker-compose.dev.yml up -d --build

# 浏览器访问
open http://localhost:5174
```

开发环境端口：

| 服务 | 宿主机端口 |
|------|-----------|
| frontend | 5174 |
| backend | 8001 |
| MySQL | 3308 |

- 修改 `backend/` 或 `skills/`：后端自动 reload，无需重建镜像。
- 修改 `frontend/`：Vite 自动热更新，无需重建镜像。
- 修改依赖文件、Dockerfile 或系统依赖：需要重新 `--build`。
- 修改 `database/init.sql`：已有 `database/mysql-data-dev/` 不会自动重放，需重置开发数据目录后再启动。
- 容器名前缀为 `chatbi-dev-*`，可以和生产式本地运行并存。

### 方式 B：宿主机启动前后端

```bash
# Backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000

# Frontend（另开终端）
cd frontend && npm install && npm run dev
```

MySQL 仍需 Docker：

```bash
docker compose up -d demo-mysql
```

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | React 18 + TypeScript + Vite + Tailwind CSS + ECharts 5 |
| 后端 | FastAPI + Python 3.11 + LiteLLM |
| 数据库 | MySQL 8.0（Docker） |
| 流式 | Server-Sent Events（SSE） |
| 质量 | black + ruff；ESLint + Prettier |

## 项目结构

```
chat-bi/
├── AGENTS.md                        # AI Agent 项目地图（规则事实源）
├── CLAUDE.md                        # 指向 AGENTS.md 的入口
├── .env.example                     # 环境变量模板
├── docker-compose.yml               # 生产式本地：MySQL + Backend + Frontend
├── docker-compose.dev.yml           # 开发热更新编排
├── data/
│   └── chatbi_sales.csv             # 示例销售数据（文件导入演示用）
├── database/
│   └── init.sql                     # 表结构、演示数据、语义层元数据
├── backend/
│   ├── main.py                      # FastAPI 入口，POST /chat SSE + POST /upload
│   ├── config.py                    # 环境变量读取（业务库 + 日志库）
│   ├── trace.py                     # Trace-ID 链路日志写入（best-effort）
│   ├── agent/
│   │   ├── protocol.py              # SkillResult 统一协议定义
│   │   ├── prompt_builder.py        # 读取 SKILL.md，构造 System Prompt
│   │   ├── planner.py               # LiteLLM 调用，生成 Skill 执行计划
│   │   ├── executor.py              # 定位并执行 Skill 脚本，归一化结果
│   │   ├── formatter.py             # SkillResult → SSE 消息
│   │   └── runner.py                # plan → execute → format 主循环
│   └── renderers/
│       ├── chart.py                 # 构造 ECharts option
│       └── kpi.py                   # 构造 KPI 卡片数据
├── frontend/
│   └── src/
│       ├── types/message.ts         # 消息类型定义
│       ├── api/client.ts            # SSE 流式客户端（透传 X-Trace-Id）
│       ├── hooks/useChat.ts         # 对话状态管理
│       └── components/
│           ├── MessageBubble.tsx    # 消息分发渲染
│           ├── ThinkingBubble.tsx   # 思考步骤（可折叠）
│           ├── ChartRenderer.tsx    # ECharts 图表
│           ├── KPICards.tsx         # KPI 卡片
│           └── ChatInput.tsx        # 输入框（支持文件拖拽/选择）
├── skills/
│   ├── _shared/                     # 脚本共用的数据库连接与协议输出工具
│   ├── chatbi-semantic-query/       # 自然语言问数
│   ├── chatbi-alias-manager/        # 语义别名管理
│   ├── chatbi-decision-advisor/     # 经营决策建议
│   └── chatbi-file-ingestion/       # CSV/XLSX 文件导入校验
└── tests/
    ├── test_agent_skill_protocol.py # SkillResult 协议单测
    ├── test_file_ingestion_skill.py # 文件导入 Skill 单测
    ├── test_trace_logging.py        # 链路日志单测
    └── test_upload_api.py           # 上传接口单测
```

## 架构流程

```
用户输入（文字 / 文件）
  → React 前端（透传 X-Trace-Id）
  ┌─ POST /upload → 文件校验 → 返回预览 JSON（chatbi-file-ingestion Skill）
  └─ POST /chat（SSE）
       → FastAPI → AgentRunner
           → prompt_builder 读取 skills/*/SKILL.md
           → planner 生成 Skill 执行计划（LiteLLM）
           → executor 执行 Skill 脚本 → MySQL chatbi_demo
           → 统一 SkillResult 协议（kind / text / data / charts / kpis）
           → formatter 转换为 SSE 消息
           → renderers 构造 ECharts option / KPI 卡片
       → SSE 流式返回
  → 前端渲染（thinking / text / chart / kpi_cards / error）
  → trace.py 将各节点日志写入 MySQL chatbi_logs（best-effort）
```

## Skills

| Skill | 功能 |
|-------|------|
| `chatbi-semantic-query` | 将自然语言转换为 SQL，查询 `chatbi_demo` 并返回表格与图表 |
| `chatbi-alias-manager` | 维护 `alias_mapping`，将业务别名映射到标准字段名 |
| `chatbi-decision-advisor` | 先计算指标事实，再按确定性规则生成经营决策建议 |
| `chatbi-file-ingestion` | 读取 CSV/XLSX，识别表头、校验类型并返回预览 JSON |

每个 Skill 的触发条件、工作流和安全边界见 `skills/<skill-name>/SKILL.md`。

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
| `CHATBI_LOG_DB_HOST` | 日志库主机（未配置时回退到业务库） |
| `CHATBI_LOG_DB_PORT` | 日志库端口 |
| `CHATBI_LOG_DB_USER` | 日志库用户 |
| `CHATBI_LOG_DB_PASSWORD` | 日志库密码 |
| `CHATBI_LOG_DB_NAME` | 日志库库名（默认 `chatbi_logs`） |
| `FRONTEND_API_BASE_URL` | 前端指向的后端地址（默认 `http://localhost:8000`） |

环境文件建议：

| 环境 | env 文件 | Compose |
|------|----------|---------|
| 生产式本地 / 测试 | `.env` | `docker-compose.yml` |
| 开发热更新 | `.env.dev`（本地，Git 忽略） | `docker-compose.dev.yml` |

## 开发文档

| 主题 | 路径 |
|------|------|
| Agent 规则与工作方式 | [AGENTS.md](AGENTS.md) |
| 系统架构与模块边界 | [docs/architecture/README.md](docs/architecture/README.md) |
| 编码规范 | [docs/conventions/README.md](docs/conventions/README.md) |
| 当前迭代任务 | [docs/plans/current-sprint.md](docs/plans/current-sprint.md) |
| 项目目标与验收标准 | [docs/goal.md](docs/goal.md) |
| Skill 能力说明 | `skills/<skill-name>/SKILL.md` |
