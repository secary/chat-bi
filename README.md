# ChatBI Demo

面向银行业务场景的对话式数据分析 Demo，让用户用中文自然语言完成问数、语义别名维护和经营决策建议生成。

## 快速开始

### 1. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env
# 编辑 .env，填入你的 OPENAI_API_KEY
```

### 2. 启动 MySQL

```bash
docker compose up -d
# MySQL 启动在 localhost:3307，表结构和演示数据自动初始化
```

### 3. 启动 Backend

```bash
# 创建虚拟环境并安装依赖
python -m venv .venv
source .venv/Scripts/activate     # Windows Git Bash
# source .venv/bin/activate       # macOS / Linux
pip install -r backend/requirements.txt

# 启动 FastAPI 服务（端口 8000）
uvicorn backend.main:app --reload --port 8000
```

### 4. 启动 Frontend

```bash
cd frontend
npm install
npm run dev
# 访问 http://localhost:5173
```

浏览器打开 `http://localhost:5173` 即可开始对话。

## 技术栈

| 层 | 技术 |
|------|--------|
| 前端 | React 18 + TypeScript + Vite + Tailwind CSS + ECharts 5 |
| 后端 | FastAPI + Python 3.11 + LiteLLM |
| 数据库 | MySQL 8.0（Docker） |
| 流式 | SSE |
| 质量 | Python black + ruff; TypeScript ESLint + Prettier |

## 项目结构

```text
chatbi/
├── AGENTS.md                          # AI Agent 项目地图
├── CLAUDE.md                          # Agent 工作手册
├── .env.example                       # 环境变量模板
├── docker-compose.yml                 # MySQL 容器
├── init_db/
│   └── init.sql                       # 表结构 + 演示数据 + 语义层
├── backend/
│   ├── main.py                        # FastAPI SSE 入口
│   ├── config.py                      # 环境变量配置
│   ├── agent/
│   │   ├── prompt_builder.py          # 读取 SKILL.md → System Prompt
│   │   └── runner.py                  # Agent 主循环 + Skill 调度
│   └── renderers/
│       ├── chart.py                   # Chart plan → ECharts option
│       └── kpi.py                     # KPI 卡片构造
├── frontend/
│   ├── src/
│   │   ├── types/message.ts           # 消息类型定义
│   │   ├── api/client.ts              # SSE 流式客户端
│   │   ├── hooks/useChat.ts           # 对话状态管理
│   │   └── components/
│   │       ├── MessageBubble.tsx       # 消息分发渲染
│   │       ├── ThinkingBubble.tsx      # 思考步骤（折叠）
│   │       ├── ChartRenderer.tsx       # ECharts 图表
│   │       ├── KPICards.tsx            # KPI 卡片
│   │       └── ChatInput.tsx           # 输入框
│   └── ...
└── skills/
    ├── chatbi-semantic-query/         # 自然语言问数
    ├── chatbi-alias-manager/          # 语义别名管理
    └── chatbi-decision-advisor/       # 经营决策建议
```

## 架构流程

```
用户输入 → React 前端 → POST /chat (SSE) → FastAPI → AgentRunner + LiteLLM
  → 读取 skills/*/SKILL.md → 选择 Skill → 执行 Python 脚本 → MySQL
  → 结果整理（图表/KPI） → SSE 流式返回 → 前端渲染
```

## 开发说明

本项目使用 **Harness Engineering** 开发模式：

- 所有规则见 `AGENTS.md`
- 当前任务见 `docs/plans/current-sprint.md`
- 项目目标见 `docs/goal.md`
- 系统架构见 `docs/architecture/overview.md`
- 模块边界见 `docs/architecture/boundaries.md`
- 编码规范见 `docs/conventions/README.md`

## 验收标准

见 `docs/goal.md`。
