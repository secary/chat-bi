# ChatBI Backend 代码架构文档

> 生成日期: 2026/05/11
> 分析范围: `backend/` 全部模块

---

## 1. 系统架构概览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FastAPI HTTP Layer                            │
│  main.py → CORS / 路由注册 / 上传处理 / 健康检查                            │
└──────────┬───────────────────────────────────────────────────────┬────────┘
           │                                                       │
     ┌─────┴──────┐                                      ┌────────┴────────┐
     │  Routes 层  │                                      │   Agent 层     │
     │  (routes/) │                                      │  (agent/)      │
     └─────┬──────┘                                      └────────┬────────┘
           │                                                       │
  ┌────────┴────────┐                                    ┌─────────┴─────────┐
  │   Repos 层      │                                    │   Services 层     │
  │ (数据访问抽象)   │                                    │ memory_service   │
  └────────┬────────┘                                    │ app_llm          │
           │                                             │ trace            │
  ┌────────┴────────┐                                    └──────────────────┘
  │   MySQL 默认同库前缀表 │
  │ business + app_* + admin_* + local logs                        │
  └─────────────────────────────────────────────────────────────────┘
```

### 数据库职责

| 数据库 | 用途 | 主要表 |
|--------|------|--------|
| `chatbi_demo` | BI 业务、应用、管理默认同库 | 业务表、语义表、视图、`chatbi_app_*`、`chatbi_admin_*` |
| `chatbi_local_logs` | 链路日志 | `chatbi_logs_trace_log` |

`CHATBI_APP_DB_*` / `CHATBI_ADMIN_DB_*` 仍保留为主动拆库时的兼容扩展点。

---

## 2. 模块功能详解

### 2.1 入口与核心配置

| 文件 | 职责 |
|------|------|
| `main.py` | FastAPI 实例创建、CORS 中间件、所有路由注册、上传文件处理（CSV/XLSX/图片，存到 `/tmp/chatbi-uploads/`）、`/health` 健康检查 |
| `config.py` | `Settings` 单例 dataclass，所有环境变量定义：LLM参数、数据库连接、jwt配置、agent行为开关 |
| `env_loader.py` | 启动时加载项目根目录 `.env` 文件 |
| `http_utils.py` | 从请求头提取或生成 `x-trace-id` |

### 2.2 认证体系

| 文件 | 职责 |
|------|------|
| `auth_password.py` | bcrypt 密码哈希与校验 |
| `auth_tokens.py` | JWT (HS256) 的创建与解码，包含 `sub`(user_id)、`role`、`iat`、`exp` 声明 |
| `auth_deps.py` | FastAPI 依赖项：`get_current_user`（JWT验证或dev模式降级）、`require_admin` 角色校验 |

### 2.3 数据访问层 (Repositories)

| 文件 | 职责 |
|------|------|
| `db_mysql.py` | MySQL 连接器：提供 `app_connection()` / `admin_connection()` 及配套的 `fetch_one/all/execute` 工具 |
| `business_db.py` | 只读访问业务数据库，调用 `connection_repo.resolve_skill_db_env()` 合并env覆盖 |
| `user_repo.py` | `app_user` 表 CRUD |
| `session_repo.py` | `chat_session` 和 `chat_message` 表 CRUD；`list_messages_for_llm()` 返回 `{role, content}` 对供 LLM 上下文；`insert_message()` 写入带 JSON payload 的消息 |
| `memory_repo.py` | `user_memory` 表管理：session summary 与 long-term profile；`suggested_prompts_for_user()` |
| `connection_repo.py` | `app_db_connection` 表 CRUD；`resolve_skill_db_env(conn_id)` 为 Skill 子进程注入数据库环境变量 |
| `skill_registry_repo.py` | `skill_registry` 表管理：按 slug 启用/禁用 Skill |
| `llm_settings_repo.py` | `llm_settings` 表：存储 LLM model/api_base/api_key（api_key 不暴露给前端） |

### 2.4 Agent 系统 (agent/)

Agent 是整个系统核心，负责 LLM 编排与 Skill 执行。

```
agent/
├── prompt_builder.py     # 系统提示词构建
├── planner.py             # LLM 调用（plan / react step）
├── executor.py            # Skill 脚本子进程执行
├── protocol.py            # Skill 输出标准化
├── observation.py         # 结果摘要压缩
├── formatter.py           # SSE 事件生成
├── intent_guard.py        # 闲聊拦截
├── query_decision.py      # query+decision 联合意图检测
├── upload_context.py      # 上传文件后续跟进的提示增强
│
├── runner.py              # 主入口：路由三种模式
├── react_runner.py        # ReAct 多步循环
├── react_followup.py      # decision advisor followup
│
├── multi_agent_registry.py # 多 Agent 注册表读写
├── multi_agent_manager.py   # Manager LLM 子任务规划（JSON）
├── multi_agent_messages.py  # 子任务 user 消息拼装
├── multi_agent_summarize.py # Manager 汇总 LLM
└── multi_agent_runner.py   # Manager 编排：规划 → 专线 → 汇总
```

#### Agent 三种运行模式

```
用户请求
  │
  ├─ multi_agents=True  →  multi_agent_runner
  │    ├─ Manager LLM（可多轮，见 max_manager_rounds）每轮一批子任务
  │    ├─ 各子任务顺序运行 ReAct/Legacy（stream_specialist + subagent 提示词）
  │    └─ Summarize LLM（Manager 口吻）汇总结果
  │
  ├─ agent_react=True   →  react_runner (ReAct 多步循环)
  │    └─ 最多 N 步: LLM决策 → Skill执行 → 结果摘要 → 下一步
  │
  └─ agent_react=False  →  runner._stream_chat_legacy (单次LLM)
       └─ LLM Plan → 1-2 步 Skill 执行
```

#### Skill 执行流程（子进程隔离）

```
executor.run_script(skill_doc, args, trace_id, skill_db_overrides)
  │
  ├─ 查找 skills/{name}/scripts/*.py
  ├─ 构建子进程 env: venv路径 / DB凭证 / trace_id
  ├─ subprocess.run([python, script, ...args])
  ├─ 期望 JSON 输出
  └─ protocol.normalize_skill_result() 标准化结果
```

#### Skill 输出标准化 (`protocol.py`)

所有 Skill 输出被规范化为:

```json
{
  "kind": "table" | "decision" | "text" | "empty",
  "text": "...",
  "data": { "rows": [...], "columns": [...] },
  "charts": [...],
  "kpis": [...],
  "chart_plan": {...}
}
```

### 2.5 渲染层 (renderers/)

| 文件 | 职责 |
|------|------|
| `chart.py` | `plan_to_option()`: 将 `chart_plan` + 数据行转为 **ECharts** option 字典；`echarts_option_to_png_bytes()` |
| `kpi.py` | `build_kpi_cards()`: 根据配置和数据构建 KPI 卡片列表 |

### 2.6 报表 / PDF (report/)

| 文件 | 职责 |
|------|------|
| `pdf_report.py` | `messages_to_html_document()`: 会话消息→HTML文档；`render_session_pdf_bytes()`: HTML→PDF (WeasyPrint, ReportLab兜底) |
| `pdf_summary.py` | `summarize_session_for_pdf()`: LLM 压缩会话为要点摘要 |
| `pdf_chart_png.py` | ECharts option → PNG 字节（matplotlib 后端） |

### 2.7 Vision 能力 (vision/)

| 文件 | 职责 |
|------|------|
| `chart_table_extract.py` | `extract_chart_table_from_image()`: 用 LiteLLM 多模态从截图提取表格；`enrich_last_user_message_with_vision()`: 检测消息中的图片路径并注入结构化 JSON（门禁见 `vision_llm_runtime.py`） |
| `vision_llm_runtime.py` | 解析专用视觉档案或已标记 `supports_vision` 的对话默认档案，单次调用 `acompletion`；`CHATBI_VISION_ALLOW_ENV_MAIN` 供无 DB 档案时的 env 主模型放行 |

### 2.8 其他服务

| 文件 | 职责 |
|------|------|
| `memory_service.py` | 每轮对话后异步刷新记忆：`format_memory_for_prompt()` 构建上下文；`refresh_memory_after_turn()` 执行 LLM 生成 session summary、trim 摘要、merge long-term profile |
| `trace.py` | 分布式追踪日志：所有模块调用 `log_event()`，通过 subprocess `mysql` CLI 写入 `chatbi_local_logs.chatbi_logs_trace_log`（或 `CHATBI_LOG_DB_*` 指定的目标） |
| `app_llm.py` | `effective_llm_params()`: 合并 `config.py` 默认值 + `llm_settings_repo` DB 值 |
| `dashboard_overview.py` | `build_dashboard_overview()`: 从业务库查询 KPI 指标（总销售额/行数/日期范围/区域数）、按区域/月份销售、语义表统计 |

### 2.9 路由层 (routes/)

| 路由文件 | 端点 | 职责 |
|----------|------|------|
| `auth_route.py` | `POST /auth/login` | 密码校验 + 返回 JWT；`GET /auth/me` 返回当前用户信息 |
| `chat_route.py` | `POST /chat` | **核心 SSE 聊天端点**（详见第3节） |
| `sessions_route.py` | `/sessions` | CRUD + 消息历史 + PDF导出 + 建议提示词 |
| `dashboard_route.py` | `GET /dashboard/overview` | BI 仪表盘概览数据 |
| `admin_db_route.py` | `/db-connections` | 数据库连接 CRUD；`GET /db-connections/current` |
| `admin_llm_route.py` | `/admin/llm-settings` | LLM 配置读写（合并后展示） |
| `admin_skills_route.py` | `/skills` | 文件系统级 Skill 管理（读/创建/更新SKILL.md/开关/删除） |
| `admin_multi_agents_route.py` | `/admin/multi-agents` | 多 Agent 注册表读写 |
| `admin_users_route.py` | `/admin/users` | 用户 CRUD（admin 专属） |

---

## 3. 请求完整流程（以 `/chat` 为例）

```
HTTP POST /chat
    │
    ▼
auth_deps.get_current_user
    │ JWT验证 / dev模式降级
    ▼
connection_repo.resolve_skill_db_env(db_connection_id)
    │ 解析数据库连接覆盖
    ▼
memory_service.format_memory_for_prompt(user_id)
    │ 构建: long-term profile + recent session summaries
    ▼
session_repo.get_session_for_user(session_id)
    │ 验证会话归属
    ▼
session_repo.insert_message(user, content)
    │ 持久化用户消息
    ▼
session_repo.update_session_title
    │ 从首条消息自动生成标题
    ▼
vision.enrich_last_user_message_with_vision
    │ 检测图片 → LLM vision 提取表格 → 注入消息
    ▼
upload_context.augment_messages_for_upload_followup
    │ 检测上传文件路径 → 提示 Agent 使用 file-ingestion
    ▼
agent.runner.stream_chat()
    │
    ├─ multi_agents=True  →  multi_agent_runner.stream_chat_multi_agent
    │     │
    │     ├─ multi_agent_manager.call_manager_plan_llm（可循环至多 max_manager_rounds）
    │     │   │ 每轮：Manager LLM 拆解子任务；可选下一轮再规划
    │     │     ▼
    │     ├─ stream_specialist(subtask_messages) × N 个子任务
    │     │   │ 每个 Agent 运行 ReAct 或 Legacy
    │     │   │   ├─ prompt_builder.build_*_system_prompt
    │     │   │   ├─ planner.call_llm_for_react_step
    │     │   │   │   │ LLM JSON 决策: call_skill / finish
    │     │   │   ├─ executor.run_script()
    │     │   │   │   │ Skill 子进程 → business_db 查询
    │     │   │   ├─ observation.summarize_observation()
    │     │   │   │   │ 结果压缩用于 LLM 上下文
    │     │   │   └─ formatter.stream_result_events()
    │     │   │       │ {text / chart / kpi_cards} SSE 事件
    │     │     ▼
    │     └─ multi_agent_summarize.call_summarize_llm
    │         │ Manager 汇总 LLM 合并各子任务结果
    │
    ├─ agent_react=True  →  react_runner.stream_chat_react
    │     │ 最多 agent_max_steps 轮循环
    │     └─ (同 stream_specialist 内部流程)
    │
    └─ agent_react=False →  runner._stream_chat_legacy
          │ 单次 LLM Plan → 可选 query+advice 两步
    ▼
EventSourceResponse (SSE)
    │
    ├─ {type: "thinking", content: "..."}
    ├─ {type: "text", content: "..."}
    ├─ {type: "chart", content: <ECharts option dict>}
    ├─ {type: "kpi_cards", content: [...]}
    ├─ {type: "error", content: "..."}
    └─ {type: "done", content: null}
    │
    ▼ finally:
    ├─ session_repo.insert_message(assistant, content, payload_json)
    ├─ session_repo.touch_session
    └─ background_tasks.add_task(memory_service.refresh_memory_after_turn)
        │ 异步: 写 session summary → trim → merge long-term profile
```

---

## 4. 关键数据模型

```
app_user
  id, username, password_hash, role (admin/user), is_active, created_at

chat_session
  id, title, user_id, created_at, updated_at

chat_message
  id, session_id, role (user/assistant/system), content, payload_json
  payload_json 可存储: {thinking, chart, kpiCards, planSummary, analysisProposal, dashboardReady, error}

user_memory
  id, user_id, kind (session_summary/long_term),
  title, content, source_session_id, updated_at

app_db_connection  (admin库)
  id, name, host, port, username, password,
  database_name, is_default, created_at

llm_settings  (admin库, id=1)
  id, model, api_base, api_key, updated_at

skill_registry  (admin库)
  skill_slug, enabled
```

---

## 5. Agent 提示词指令架构

### 单步模式 (Legacy)
```
AGENT_SYSTEM_INSTRUCTION
  → Skill 选择规则 / JSON输出格式 / 可视化约束
```

### 多步模式 (ReAct)
```
AGENT_REACT_INSTRUCTION
  → JSON输出格式 / action规范 / observation处理 / 可视化规则
```

两种模式由 `prompt_builder.build_system_prompt()` 和 `build_react_system_prompt()` 分别构建。

---

## 6. Skill 架构

Skill 目录结构:
```
skills/
├── chatbi-semantic-query/
│   ├── SKILL.md          # YAML frontmatter + 描述
│   └── scripts/
│       └── run.py       # 执行脚本，输出 JSON
├── chatbi-decision-advisor/
│   ├── SKILL.md
│   └── scripts/
│       └── run.py
...其他 Skill
_agents/
└── registry.yaml        # 多 Agent 注册表
```

### Skill 执行隔离模型

```
Main Process                    Subprocess (Skill)
┌──────────────────┐            ┌──────────────────┐
│ executor.py      │ ─env───▶   │ scripts/run.py   │
│ (构建env字典)    │            │ (访问 business_db)│
│                 │ ◀──JSON─── │                  │
└──────────────────┘            └──────────────────┘
```

Skill 通过环境变量获得数据库凭证，**主进程不直接访问业务数据库**，实现安全隔离。

---

## 7. 核心技术栈

| 类别 | 技术 |
|------|------|
| Web 框架 | FastAPI + Starlette |
| LLM 接口 | LiteLLM（统一封装 OpenAI/DeepSeek/阿里等） |
| 数据库 | MySQL（默认同库前缀表 + 独立日志库） |
| 认证 | JWT (PyJWT) + bcrypt |
| 密码学 | passlib (bcrypt) |
| 实时通信 | SSE (sse_starlette) |
| 图表渲染 | ECharts (前端) / matplotlib (PDF PNG) |
| PDF 生成 | WeasyPrint + ReportLab |
| 追踪日志 | MySQL + subprocess mysql CLI |

---

## 8. 架构设计要点

1. **Skill 隔离执行**: Skill 以子进程运行，通过 env 注入 DB 凭证，主进程不直接访问业务库
2. **ReAct 循环**: LLM 生成 JSON 决策 → 执行 Skill → 摘要观察 → 循环，最大步数可配置
3. **三级记忆**: chat_message (短时) → session_summary (中时) → long_term_profile (长时)
4. **三库分离**: app(用户数据) / admin(配置) / business(BI数据) 逻辑分离
5. **SSE 流式响应**: `/chat` 实时推送 thinking/text/chart/kpi_cards，最终汇聚落库
6. **多 Agent 编排**: Router LLM 选 Agent → 并行执行 → Summarize LLM 合并
7. **配置合并优先级**: env defaults < DB records < per-request overrides
