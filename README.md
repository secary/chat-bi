# ChatBI Demo

面向银行业务场景的对话式数据分析 Demo，让用户用中文自然语言完成问数、语义别名维护和经营决策建议生成。

## 快速开始

```bash
# 启动 MySQL + Backend
docker compose up

# 前端本地开发
cd frontend
npm install
npm run dev
```

> 具体依赖和启动命令会随 MVP 实现补齐；当前以 `ChatBI_frontend_agent_PRD.md` 和 `docs/plans/current-sprint.md` 为准。

## 项目结构

```text
chatbi/
├── AGENTS.md
├── ChatBI_frontend_agent_PRD.md
├── README.md
├── .cursor/
│   └── rules/
│       └── harness-engineering.mdc
├── docs/
│   ├── architecture/
│   │   ├── boundaries.md
│   │   └── overview.md
│   ├── conventions/
│   │   └── README.md
│   ├── design/
│   │   └── feature-template.md
│   ├── plans/
│   │   └── current-sprint.md
│   ├── reference/
│   │   └── README.md
│   └── goal.md
├── init_db/
├── skills/
│   ├── chatbi-semantic-query/
│   ├── chatbi-alias-manager/
│   └── chatbi-decision-advisor/
├── backend/
└── frontend/
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
