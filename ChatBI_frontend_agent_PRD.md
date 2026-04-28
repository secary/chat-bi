# ChatBI Demo — 产品需求文档（PRD）

**版本**：v1.0  
**状态**：已确认，待开发  
**日期**：2026-04-28  

---

## 目录

1. [产品概述](#1-产品概述)
2. [用户与使用场景](#2-用户与使用场景)
3. [系统架构](#3-系统架构)
4. [Skill 与脚本规范](#4-skill-与脚本规范)
5. [功能需求](#5-功能需求)
6. [前端界面需求](#6-前端界面需求)
7. [数据库设计](#7-数据库设计)
8. [非功能需求](#8-非功能需求)
9. [目录结构](#9-目录结构)
10. [开发里程碑](#10-开发里程碑)
11. [开放问题与约束](#11-开放问题与约束)

---

## 1. 产品概述

### 1.1 产品定位

ChatBI 是一个面向银行业务场景的**对话式数据分析 Demo**。用户以自然语言提问，系统通过 AI Agent 自动理解意图、选择对应的分析技能（Skill）、调用技能内置脚本查询 MySQL 数据库或维护语义层，最终以文字结论、动态图表、KPI 卡片等形式呈现分析结果。

### 1.2 核心价值

- **零门槛**：不需要写 SQL，用中文直接提问
- **可解释**：前端实时展示 Agent 思考过程，分析结果透明可信
- **可扩展**：Skill 以独立目录封装说明文档和脚本入口，新增业务分析场景只需添加 `skills/<skill-name>/`，无需改动主流程

### 1.3 Demo 范围

本期为单用户 Demo，不涉及登录、权限、多租户。核心目标是跑通「System Prompt 声明 Skill → Agent 选择 Skill → Skill 指导脚本与图表策略 → 脚本执行 → 可交互结果渲染」完整链路。

---

## 2. 用户与使用场景

### 2.1 目标用户

银行中台/业务管理人员（如支行经理、区域主管），具备业务知识，不懂 SQL。

### 2.2 典型使用场景

| 场景 | 示例提问 |
|---|---|
| 经营指标问数 | "2026 年 4 月华东目标完成率是多少？" |
| 多维度排行 | "按区域看 2026 年 1 月到 4 月销售额排行" |
| 多轮上下文追问 | "刚才最高的区域，它的毛利率怎么样？" |
| 语义别名补充 | "把成交方式识别为渠道，下次问这个词也能查" |
| 经营决策建议 | "给我一份线上渠道软件服务的经营建议" |

### 2.3 多轮上下文要求

用户在同一会话中可引用前序对话的数据，例如：

> 第一轮：「哪个区域销售额最高？」→ 华东  
> 第二轮：「它的目标完成率和毛利率呢？」→ Agent 自动关联「华东」上下文

---

## 3. 系统架构

### 3.1 分层架构

```
用户自然语言输入
        │
        ▼
  ┌─────────────┐
  │    Agent    │  ← LiteLLM 统一调用（gpt-4o / claude 等）
  │  Runner     │  ← System Prompt 内含所有 SKILL.md 描述
  └──────┬──────┘
         │ 模型自主选择 Skill（方案 A：纯 LLM 决策）
         ▼
  ┌─────────────┐
  │   Skill     │  业务语义层：semantic query / alias manager / decision advisor
  │  Directory  │  读取 SKILL.md：脚本入口 + 可视化建议 + 安全边界
  └──────┬──────┘
         │ Skill 脚本入口执行
         ▼
  ┌─────────────┐
  │   Scripts   │  chatbi_semantic_query.py / add_alias_mapping.py
  │  + Renderer │  generate_decision_advice.py / ECharts option builder
  └──────┬──────┘
         │
         ▼
  MySQL 8.0 / 语义层元数据 / 统计计算 / 前端交互式图表渲染
```

### 3.2 数据流（单轮）

1. 前端通过 HTTP POST `/chat` 发送消息 + 会话历史
2. FastAPI/AgentRunner 读取 `skills/*/SKILL.md`，将技能用途、工作流、可视化建议、安全边界注入 System Prompt
3. AgentRunner 调用 LiteLLM，模型根据用户意图选择 `chatbi-semantic-query`、`chatbi-alias-manager` 或 `chatbi-decision-advisor`
4. AgentRunner 按 Skill 文档调用对应 `scripts/` 入口，并传入问题、输出格式和数据库连接参数
5. 脚本通过 MySQL CLI 查询或维护语义层，返回 Markdown、表格或 JSON 结构化结果
6. AgentRunner 结合用户意图、数据形态和 Skill 可视化建议，选择柱状图、折线图、饼图、Treemap 或 KPI 卡片
7. 后端 renderer 将结构化结果转换为 ECharts option，并附带 tooltip、legend、筛选、高亮等交互配置
8. AgentRunner 将结果通过 SSE 流式推送 thinking / text / chart / kpi_cards / error 消息，前端负责展示和交互

### 3.3 技术选型

| 层级 | 技术 | 说明 |
|---|---|---|
| 模型调用 | LiteLLM | 统一接口，env 变量切换模型和 API Key |
| 后端框架 | FastAPI + Python 3.11 | async 支持，SSE 原生友好 |
| 数据库 | MySQL 8.0（Docker） | 端口 3307，库名 `chatbi_demo` |
| MySQL 访问 | mysql CLI | Skill 脚本通过本地 `mysql` 命令执行确定性查询 |
| 前端框架 | React 18 + TypeScript | 组件化，类型安全 |
| 图表库 | Apache ECharts 5 | 支持柱状图、折线图、饼图、树状图，动态交互 |
| 样式 | Tailwind CSS | 极简主义，快速布局 |
| 流式通信 | SSE（Server-Sent Events） | 服务端推送，前端 EventSource 接收 |
| 容器化 | Docker Compose | MySQL + Backend 一键启动 |

---

## 4. Skill 与脚本规范

### 4.1 Skill 定义规范

每个 Skill 是 `skills/` 目录下的一个独立目录，目录内必须包含 `SKILL.md`，可选包含 `scripts/` 下的可执行脚本：

```text
skills/
└── chatbi-semantic-query/
    ├── SKILL.md
    └── scripts/
        └── chatbi_semantic_query.py
```

`SKILL.md` 必须包含 YAML frontmatter 和正文说明：

```markdown
---
name: chatbi-semantic-query
description: Use when an agent needs to answer Chinese natural-language data questions against the local ChatBI demo MySQL database.
---

# ChatBI Semantic Query

## Workflow
1. Use `scripts/chatbi_semantic_query.py` for natural-language metric questions.
2. Prefer `--show-sql` when the generated SQL should be inspected.
3. Prefer `--json` when another component needs structured output.

## Visualization Guidance
- 分类维度对比、排行：bar chart
- 月份或时间趋势：line chart
- 构成、占比、份额：pie chart

## Safety
Use this skill for read-only semantic queries. Do not execute destructive SQL.
```

**目录契约**：

| 项 | 要求 |
|---|---|
| `name` | Skill 唯一标识，必须与目录名一致 |
| `description` | 触发条件说明，会被 Agent 注入 System Prompt |
| `Workflow` | Agent 执行该 Skill 的步骤和判断边界 |
| `Commands` | 可直接运行的脚本命令示例 |
| `Visualization Guidance` | 查询结果适合生成的图表类型、触发条件和交互建议 |
| `scripts/` | Skill 的确定性执行入口，负责查询、语义层维护或建议生成 |
| `Safety` | SQL 读写边界、别名写入范围、是否允许模型改写结果 |

**发现机制**：AgentRunner 启动或处理请求时读取 `skills/*/SKILL.md`，将 `name`、`description`、工作流、可视化建议和安全约束注入 System Prompt。模型只负责选择合适 Skill、组织参数和选择展示意图；确定性数据查询、别名写入、决策建议生成由 Skill 自带脚本完成，ECharts 配置由后端 renderer 生成。

### 4.2 脚本能力规范

本期不强制建设独立的后端工具注册层。原子能力优先封装在 Skill 脚本中：

| 能力 | 当前承载方式 |
|---|---|
| 语义解析与 SQL 生成 | `chatbi-semantic-query/scripts/chatbi_semantic_query.py` |
| MySQL 查询 | 脚本通过本地 `mysql` CLI 执行，连接参数来自 `CHATBI_DB_*` |
| 统计与决策规则 | `chatbi-decision-advisor/scripts/generate_decision_advice.py` |
| 语义别名维护 | `chatbi-alias-manager/scripts/add_alias_mapping.py` |
| 图表策略 | `SKILL.md` 的 `Visualization Guidance` 给出推荐图表和交互方式 |
| 图表生成 | 后端 renderer 根据脚本 JSON 输出生成 ECharts option，前端负责渲染和交互 |

如果后续需要将能力服务化，可再抽象 `tools/` 目录和 LiteLLM function schema；但当前 PRD 以现有 `skills/` 目录为准。

### 4.3 初始 Skill 清单

| Skill | 触发场景 | 脚本入口 | 输出 | 可视化建议 |
|---|---|---|---|---|
| `chatbi-semantic-query` | 中文自然语言问数、指标查询、趋势、排名、筛选、SQL 解释 | `scripts/chatbi_semantic_query.py` | 表格；`--json` 结构化行；`--show-sql` 生成 SQL | 对比/排名用柱状图；时间趋势用折线图；构成占比用饼图；单点摘要用 KPI |
| `chatbi-alias-manager` | 新增中文同义词、业务别名、指标/维度映射 | `scripts/add_alias_mapping.py` | 插入状态；可选 `--print-init-sql` 输出初始化 SQL values 元组 | 默认文本状态；验证原问题时交给 `chatbi-semantic-query` 生成图表 |
| `chatbi-decision-advisor` | 经营建议、管理建议、下一步动作、决策意见 | `scripts/generate_decision_advice.py` | Markdown 决策建议；`--json` 结构化 facts + advices | 总览用 KPI；月度事实用折线图；区域/渠道/产品排名用柱状图 |

### 4.4 数据库连接与安全边界

三个 Skill 脚本默认连接本地演示库：

| 配置项 | 默认值 | 环境变量 |
|---|---|---|
| Host | `127.0.0.1` | `CHATBI_DB_HOST` |
| Port | `3307` | `CHATBI_DB_PORT` |
| Database | `chatbi_demo` | `CHATBI_DB_NAME` |
| User | `demo_user` | `CHATBI_DB_USER` |
| Password | `demo_pass` | `CHATBI_DB_PASSWORD` |

安全约束：

- `chatbi-semantic-query` 只生成并执行受语义层约束的 `SELECT` 查询，不执行破坏性 SQL。
- `chatbi-decision-advisor` 先计算确定性指标事实，再按显式规则生成建议；如使用 LLM，只允许改写或摘要事实与建议，不允许编造结论。
- `chatbi-alias-manager` 只允许向 `alias_mapping` 插入已验证标准指标/维度的别名，不创建新指标或新维度，不默认更新或删除已有别名。

---

## 5. 功能需求

### 5.1 Agent 对话能力

| 需求 ID | 需求描述 | 优先级 |
|---|---|---|
| F-01 | 支持中文自然语言提问，模型理解业务意图 | P0 |
| F-02 | 多轮上下文：后续问题可引用前轮分析结果 | P0 |
| F-03 | 模型自主选择 Skill，无需用户指定（方案 A） | P0 |
| F-04 | Skill 内部按 `SKILL.md` 工作流调用确定性脚本入口 | P0 |
| F-05 | SSE 流式推送，逐步呈现结果 | P0 |
| F-06 | Agent 思考步骤实时展示（选中哪个 Skill、调用哪个脚本、执行状态） | P0 |

### 5.2 Skill / 脚本扩展能力

| 需求 ID | 需求描述 | 优先级 |
|---|---|---|
| F-07 | 新增 Skill 只需添加 `skills/<skill-name>/SKILL.md`，可选增加 `scripts/` 入口，System Prompt 自动更新 | P0 |
| F-08 | Skill 脚本支持通过 `CHATBI_DB_*` 环境变量覆盖数据库连接 | P0 |
| F-09 | 删除 Skill 只需移除对应目录，无需改动 Agent 主流程代码 | P0 |

### 5.3 图表与可视化能力

| 需求 ID | 需求描述 | 优先级 |
|---|---|---|
| F-10 | 支持柱状图（区域对比、指标排名） | P0 |
| F-11 | 支持折线图（时间趋势、季度走势） | P0 |
| F-12 | 支持饼图（资产构成、占比分析） | P0 |
| F-13 | 支持树状图 Treemap（多维度层级数据） | P1 |
| F-14 | 图表支持 tooltip 悬停展示详情 | P0 |
| F-15 | 图表支持图例点击筛选 | P0 |
| F-16 | 图表支持数据点点击高亮 | P0 |
| F-17 | 图表卡片内提供图表类型切换按钮（柱状 / 折线 / 饼图） | P1 |
| F-18 | Agent 根据 Skill 可视化建议、用户意图和数据形态选择默认图表类型 | P0 |
| F-19 | 图表消息包含交互配置，如 legend 筛选、tooltip、brush/dataZoom、点击高亮或下钻参数 | P1 |

### 5.4 消息类型规范

前端消息气泡支持以下类型，后端 SSE 推送时携带 `type` 字段区分：

| type | 描述 | 展示形式 |
|---|---|---|
| `thinking` | Agent 思考步骤 | 灰色小气泡，逐步追加步骤，支持折叠 |
| `text` | 文字结论 | 主气泡，支持加粗高亮关键词 |
| `chart` | ECharts 图表配置 | 内嵌图表卡片，含标题栏和交互控件 |
| `kpi_cards` | KPI 数字卡片组 | 横排卡片，含标签、数值、颜色语义 |
| `error` | 错误提示 | 红色边框气泡，含错误描述 |

### 5.5 SSE 事件格式

```
// 思考步骤
data: {"type": "thinking", "step": "选择 Skill：chatbi-semantic-query", "status": "done"}

// 思考步骤（进行中）
data: {"type": "thinking", "step": "生成只读 SQL 并执行 mysql CLI 查询", "status": "running"}

// 文字结论
data: {"type": "text", "content": "2026 年 4 月华东区域销售额为 **128.50 万元**，目标完成率为 **103.2%**..."}

// 图表
data: {
  "type": "chart",
  "title": "销售额趋势 / 2026 年 1-4 月",
  "chart_type": "line",
  "config": { /* ECharts option */ },
  "interactions": {
    "tooltip": true,
    "legend_filter": true,
    "data_zoom": true,
    "click_highlight": true
  }
}

// KPI 卡片组
data: {"type": "kpi_cards", "cards": [
  {"label": "销售额", "value": "128.50 万", "semantic": "neutral"},
  {"label": "目标完成率", "value": "103.2%", "semantic": "success"},
  {"label": "毛利率", "value": "35.6%", "semantic": "neutral"}
]}

// 结束标志
data: {"type": "done"}
```

---

## 6. 前端界面需求

### 6.1 整体布局

```
┌────────────────────────────────────────────────┐
│  侧边栏（200px）  │  主内容区（自适应）            │
│                  │  ┌──── 顶栏（44px）──────┐   │
│  Logo            │  │ 会话标题      [导出]   │   │
│  [+ 新建对话]    │  └───────────────────────┘   │
│                  │                               │
│  最近            │  ┌──── 对话区（滚动）──────┐  │
│  › 区域销售分析   │  │  用户气泡（右对齐）      │  │
│    月度收入趋势   │  │  思考气泡（左，灰色）    │  │
│    经营决策建议   │  │  AI 回答气泡（左）       │  │
│                  │  │    ├── 文字结论          │  │
│  数据源          │  │    ├── 图表卡片          │  │
│  ↑ 上传文件      │  │    └── KPI 卡片组        │  │
│  ○ 连接数据库    │  └───────────────────────┘   │
│                  │                               │
│  [用户头像] 张   │  ┌──── 输入区（固定底部）──┐  │
│                  │  │ [输入框]        [发送]  │   │
│                  │  │ gpt-4o · via LiteLLM   │   │
│                  │  └───────────────────────┘   │
└────────────────────────────────────────────────┘
```

### 6.2 设计风格

- **极简主义**：无渐变、无阴影、纯靠 0.5px 线条和间距划分层次
- **配色**：白色主背景，浅灰次级表面，黑色强调（异常数据高亮用语义红/橙）
- **字体**：系统 sans-serif，层级通过字号（10/12/13/18/24px）和字重（400/500）区分
- **圆角**：8px（组件内），12px（卡片级）

### 6.3 组件清单

| 组件 | 文件 | 描述 |
|---|---|---|
| 侧边栏 | `Sidebar.tsx` | 历史会话列表、数据源入口、用户信息 |
| 对话窗口 | `ChatWindow.tsx` | 消息列表，自动滚动到底部 |
| 消息路由 | `MessageBubble.tsx` | 根据 `type` 分发渲染不同组件 |
| 思考气泡 | `ThinkingBubble.tsx` | 逐步展示 Agent 步骤，支持折叠展开 |
| 图表渲染 | `ChartRenderer.tsx` | 内嵌 ECharts，支持类型切换 |
| KPI 卡片组 | `KPICards.tsx` | 横排数字卡片，语义着色 |
| 输入框 | `ChatInput.tsx` | 文本输入 + 发送按钮 + 模型标签 |

### 6.4 状态管理

使用 `useChat` 自定义 Hook 统一管理：

- 当前会话消息列表（`Message[]`）
- SSE 连接状态
- 历史会话列表（`Session[]`）
- 当前输入内容
- Loading 状态

---

## 7. 数据库设计

### 7.1 连接信息

| 项 | 值 |
|---|---|
| 镜像 | mysql:8.0 |
| 端口 | 3307（宿主机）→ 3306（容器内）|
| 库名 | chatbi_demo |
| 用户 | demo_user |
| 密码 | demo_pass |
| 字符集 | utf8mb4_unicode_ci |

### 7.2 核心表

**sales_order** — 销售订单

| 字段 | 类型 | 说明 |
|---|---|---|
| id | BIGINT PK | 主键 |
| order_date | DATE | 订单日期 |
| region | VARCHAR(50) | 区域，如华东、华南、华北、西南 |
| department | VARCHAR(50) | 负责部门 |
| product_category | VARCHAR(50) | 产品类别，如软件服务、数据产品、咨询服务 |
| product_name | VARCHAR(80) | 具体产品名称 |
| channel | VARCHAR(50) | 成交渠道，如线上、渠道、直销 |
| customer_type | VARCHAR(50) | 客户类型，如企业客户、中小客户 |
| sales_amount | DECIMAL(12,2) | 销售额 |
| order_count | INT | 订单数 |
| customer_count | INT | 客户数 |
| gross_profit | DECIMAL(12,2) | 毛利 |
| target_amount | DECIMAL(12,2) | 目标销售额 |

**customer_profile** — 客户画像（月度快照）

| 字段 | 类型 | 说明 |
|---|---|---|
| id | BIGINT PK | 主键 |
| stat_month | DATE | 统计月份 |
| region | VARCHAR(50) | 区域 |
| customer_type | VARCHAR(50) | 客户类型 |
| new_customers | INT | 新增客户数 |
| active_customers | INT | 活跃客户数 |
| retained_customers | INT | 留存客户数 |
| churned_customers | INT | 流失客户数 |

### 7.3 语义层元数据表

**metric_definition** — 指标定义

| 字段 | 类型 | 说明 |
|---|---|---|
| metric_name | VARCHAR(100) | 指标中文名，如销售额、毛利率、目标完成率 |
| metric_code | VARCHAR(100) | 指标编码 |
| source_table | VARCHAR(100) | 来源表 |
| formula | TEXT | 指标计算公式 |
| business_caliber | TEXT | 业务口径说明 |

**dimension_definition** — 维度定义

| 字段 | 类型 | 说明 |
|---|---|---|
| dimension_name | VARCHAR(100) | 维度中文名，如区域、月份、渠道 |
| field_name | VARCHAR(100) | 数据库字段名 |
| source_table | VARCHAR(100) | 来源表 |

**alias_mapping** — 中文别名映射

| 字段 | 类型 | 说明 |
|---|---|---|
| alias_name | VARCHAR(100) | 用户可能使用的业务说法，如营收、成交方式 |
| standard_name | VARCHAR(100) | 标准指标或维度名 |
| object_type | VARCHAR(20) | `指标` 或 `维度` |
| description | TEXT | 映射说明 |

---

## 8. 非功能需求

| 需求 | 描述 |
|---|---|
| 用户体系 | 单用户，无需登录，无多租户隔离 |
| 模型切换 | 通过 `.env` 配置 `LLM_MODEL` 和 API Key，运行时不需改代码 |
| 扩展性 | Skill 新增删除只改 `skills/<skill-name>/SKILL.md` 与可选 `scripts/` 文件 |
| 部署方式 | `docker compose up` 一键启动 MySQL + Backend；前端 `npm run dev` 本地开发 |
| 数据库配置 | Skill 脚本默认连接 `127.0.0.1:3307/chatbi_demo`，支持 `CHATBI_DB_HOST`、`CHATBI_DB_PORT`、`CHATBI_DB_USER`、`CHATBI_DB_PASSWORD`、`CHATBI_DB_NAME` 覆盖 |
| 数据安全 | 问数和决策建议 Skill 只执行 `SELECT`；别名管理 Skill 仅向 `alias_mapping` 插入已验证别名 |
| 结果可信 | 决策建议必须先计算指标事实，再按确定性规则生成建议；LLM 只做选择、摘要和表达优化 |
| 错误处理 | SQL 执行失败、模型调用超时、脚本异常均通过 `error` 类型消息反馈给前端 |
| 响应速度 | SSE 首字节（第一个 thinking 步骤）应在 1s 内到达 |
| 代码规范 | Python：black + ruff；TypeScript：ESLint + Prettier |

---

## 9. 目录结构

```
chatbi/
├── docker-compose.yml               # MySQL + Backend 容器编排
├── .env.example                     # 环境变量模板（LLM_MODEL / API Keys / CHATBI_DB_*）
├── .env                             # 本地配置，不提交 git
│
├── init_db/
│   ├── init.sql                     # 表结构 + 示例数据 + 语义层元数据
│   └── demo_metadata.sql            # 可选：元数据补充
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt             # fastapi, litellm, uvicorn
│   ├── main.py                      # FastAPI 入口，注册路由
│   ├── config.py                    # 环境变量读取
│   │
│   ├── agent/
│   │   ├── runner.py                # Agent 主循环：LiteLLM 调用 + Skill 脚本调度
│   │   └── prompt_builder.py        # 读取 skills/*/SKILL.md 动态生成 System Prompt
│   │
│   └── renderers/                   # 可选：脚本结果转前端消息
│       ├── chart_builder.py         # JSON 结果生成 ECharts option
│       └── kpi_builder.py           # JSON 结果生成 KPI 卡片
│
├── skills/                          # ⭐ Agent Skill 目录
│   ├── chatbi-semantic-query/
│   │   ├── SKILL.md                 # 中文自然语言问数说明
│   │   └── scripts/
│   │       └── chatbi_semantic_query.py
│   ├── chatbi-alias-manager/
│   │   ├── SKILL.md                 # 语义别名维护说明
│   │   └── scripts/
│   │       └── add_alias_mapping.py
│   └── chatbi-decision-advisor/
│       ├── SKILL.md                 # 决策建议生成说明
│       └── scripts/
│           └── generate_decision_advice.py
│
└── frontend/
    ├── package.json
    ├── tsconfig.json
    ├── vite.config.ts
    └── src/
        ├── App.tsx                  # 根组件，路由
        ├── main.tsx
        ├── components/
        │   ├── Sidebar.tsx          # 左侧边栏
        │   ├── ChatWindow.tsx       # 主对话区，消息列表
        │   ├── MessageBubble.tsx    # 消息类型路由分发
        │   ├── ThinkingBubble.tsx   # Agent 思考步骤气泡
        │   ├── ChartRenderer.tsx    # ECharts 动态图表
        │   ├── KPICards.tsx         # KPI 数字卡片组
        │   └── ChatInput.tsx        # 底部输入框
        ├── hooks/
        │   └── useChat.ts           # SSE 连接 + 消息状态管理
        └── types/
            └── message.ts           # Message / Session 类型定义
```

---

## 10. 开发里程碑

| 阶段 | 内容 | 产出物 |
|---|---|---|
| Step 1 | 数据库初始化 | `init_db/init.sql`，包含业务数据表、语义层元数据表和示例数据 |
| Step 2 | Skill 脚本验证 | 跑通 `chatbi_semantic_query.py`、`add_alias_mapping.py`、`generate_decision_advice.py` 的关键命令 |
| Step 3 | Skill 文档适配 | `skills/` 下 3 个 Skill 的 `SKILL.md` 与脚本入口保持一致，触发场景和安全边界清晰 |
| Step 4 | Agent 层实现 | `agent/runner.py` + `prompt_builder.py`，完成 `SKILL.md` 读取、Skill 选择、脚本调用和 LiteLLM 汇总 |
| Step 5 | FastAPI 接口 | `POST /chat` SSE 接口，消息格式符合第 5.5 节规范 |
| Step 6 | 前端界面 | React 组件全部实现，SSE 接收与渲染 |
| Step 7 | 联调验收 | `docker compose up` + 前端 dev server，跑通问数、别名补充、决策建议 3 类典型场景 |

---

## 11. 开放问题与约束

| 编号 | 问题 | 状态 |
|---|---|---|
| Q-01 | `init.sql` 与 `demo_metadata.sql` 中已有哪些表和数据？需确认避免冲突 | 待确认 |
| Q-02 | LiteLLM 默认使用哪个模型？本地开发是否有 API Key 预算限制？ | 待确认 |
| Q-03 | 前端是否需要 Docker 化，还是纯本地 `npm run dev`？ | 已定：本地 dev |
| Q-04 | 图表颜色主题是否需要与品牌色对齐，或使用默认 ECharts 主题？ | 待定 |
| Q-05 | 后续是否需要支持文件上传（xlsx/csv）作为数据源？ | 超出本期范围 |

---

*文档结束。确认后进入 Step 1 开发阶段。*
