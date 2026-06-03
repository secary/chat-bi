# ChatBI Backend 代码架构文档

> 更新日期: 2026/05/18  
> 分析范围: `backend/` 全部模块  
> 面向功能与 Agent 行为的说明见 [docs/guide/tech-guide.md](guide/tech-guide.md)；模块边界见 [docs/architecture/README.md](architecture/README.md)。

---

## 1. 系统架构概览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FastAPI HTTP Layer                            │
│  main.py → CORS / 路由注册 / POST /upload / POST /abort / 健康检查         │
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
  │   MySQL        │
  │ chatbi_demo                     │
  └─────────────────────────────────────────────────────────────────────────┘
```

### 数据库职责

| 数据库 | 用途 | 主要表前缀 / 表 |
|--------|------|-----------------|
| `chatbi_demo` | BI 业务、应用、管理、链路日志 | 业务表、语义层、`app_*`、`app_chat_session`、`app_chat_message`、`app_user_memory`、`admin_db_connection`、`admin_llm_settings`、`admin_llm_model_profile`、`admin_skill_registry`、`log` |

**Docker compose**：
- 开发环境通过 `scripts/start_dev.sh` 初始化本机 MySQL；`docker-compose.yml` 默认启动生产式 MySQL 与一体应用容器，并初始化 `chatbi_demo` 一个库。

`CHATBI_APP_DB_*` / `CHATBI_ADMIN_DB_*` 为兼容扩展点；默认沿用 `chatbi_demo`。

---

## 2. 模块功能详解

### 2.1 入口与核心配置

| 文件 | 职责 |
|------|------|
| `main.py` | FastAPI 实例、CORS、路由注册、`POST /upload`（`/tmp/chatbi-uploads/`）、`/health` |
| `config.py` | `Settings`：`CHATBI_AGENT_REACT`、`CHATBI_AGENT_MAX_STEPS`、DB、JWT、记忆开关等 |
| `env_loader.py` | 加载根目录 `.env` / `.env.dev` |
| `http_utils.py` | 提取或生成 `x-trace-id` |
| `db_tables.py` | 表名常量（`app_*`、`admin_*`、`log`） |

### 2.2 认证体系

| 文件 | 职责 |
|------|------|
| `auth_password.py` | bcrypt 哈希与校验 |
| `auth_tokens.py` | JWT (HS256)：`sub`、`role`、`iat`、`exp` |
| `auth_deps.py` | `get_current_user`（JWT 或 `CHATBI_AUTH_ENABLED=false` 降级）、`require_admin` |

### 2.3 数据访问层 (Repositories)

| 文件 | 职责 |
|------|------|
| `db_mysql.py` | `app_connection()` / `admin_connection()` 及 fetch/execute 工具 |
| `business_db.py` | 只读业务库；`connection_repo.resolve_skill_db_env()` 合并连接覆盖 |
| `user_repo.py` | `app_user` CRUD |
| `session_repo.py` | `app_chat_session` / `app_chat_message`；`list_messages_for_llm()`；`load_messages_ui()` 恢复 `planSummary` / `analysisProposal` / `dashboardReady` |
| `memory_repo.py` | `app_user_memory`：session_summary、long_term；`suggested_prompts_for_user()` |
| `connection_repo.py` | `admin_db_connection` CRUD；`resolve_skill_db_env(conn_id)` 供 Skill 子进程 |
| `skill_registry_repo.py` | `admin_skill_registry`：按 slug 启用/禁用 |
| `llm_settings_repo.py` | `admin_llm_settings`：全局 LLM 行 + `active_profile_id` |
| `llm_profile_repo.py` | `admin_llm_model_profile`：多 Profile、排序、健康检查字段 |

### 2.4 Agent 系统 (agent/)

```
agent/
├── prompt_builder.py      # System Prompt + Skill 元数据摘录
├── prompt_subagent.py       # 多专线下 ReAct/Legacy 子 agent 提示
├── planner.py               # LiteLLM：plan / react step / manager plan
├── executor.py              # Skill 子进程（轮询 abort）
├── protocol.py              # SkillResult 归一化
├── observation.py           # Observation 摘要（含 comparison_period）
├── formatter.py             # SkillResult → SSE 事件
├── intent_guard.py          # 寒暄短路
├── query_decision.py        # query + decision 联合意图
├── upload_context.py        # 上传路径跟进提示
├── data_source_intent.py    # 演示库 / 上传文件意图与路径检测
├── execution_decider.py     # single / multi / ask 执行模式预审计
├── execution_audit.py       # single 补救与 multi 事实收束审计
├── context_window.py        # 滑动窗口 + 摘要注入（ReAct / Manager）
├── abort_state.py           # 按 trace_id 的中止 Event
├── abort_async.py           # await_with_abort 包装 LLM
├── runner.py                # stream_chat 三分支入口
├── react_runner.py          # ReAct 多步
├── react_followup.py        # decision advisor 跟进
├── multi_agent_registry.py  # registry.yaml 读写
├── multi_agent_manager.py   # Manager 规划 LLM + 上传/采纳线索
├── multi_agent_messages.py  # 子任务 messages
├── multi_agent_summarize.py # 汇总 LLM
└── multi_agent_runner.py    # 多轮规划 → 专线顺序执行 → 汇总 / 短路
```

#### Agent 三种运行模式

```
用户请求 (multi_agents, CHATBI_AGENT_REACT)
  │
  ├─ multi_agents=True  →  multi_agent_runner
  │    ├─ Manager LLM（≤ max_manager_rounds）每轮一批子任务
  │    ├─ 子任务顺序 stream_specialist（非并行）
  │    ├─ 可因 chatbi-auto-analysis 中间件短路
  │    └─ Summarize LLM（或无 block 时降级单 Agent）
  │
  ├─ agent_react=True（默认）→  react_runner
  │    └─ ≤ agent_max_steps：LLM → call_skill/ask/finish → Observation
  │
  └─ agent_react=False  →  _stream_chat_legacy
       └─ 单次 Plan → 1～2 步 Skill（可选 query → decision-advisor）
```

执行过程中通过 `is_aborted(trace_id)` 与 `POST /abort` 协作中止；LLM 调用经 `abort_async.await_with_abort`。

#### Prompt 拼装顺序

1. `build_*_system_prompt(skills)`：`AGENT_*_INSTRUCTION` + 各 Skill 的 **选用时机 / 不要用 / 必备上下文**（YAML frontmatter）+ 正文节选。
2. 可选 `role_prompt`（多专线）。
3. 可选 `memory_block`（最外层）。
4. **无** `skill_call_validator`：不在执行脚本前硬校验 Skill 选用。

ReAct / Manager 送入 LLM 前，`context_window.build_react_context` / `build_manager_context` 压缩历史。

#### Skill 执行流程

```
executor.run_script(skill_doc, args, trace_id, skill_db_overrides)
  ├─ skills/{slug}/scripts/*.py
  ├─ 子进程 env：DB 凭证、trace_id
  ├─ subprocess（执行中可检测 abort）
  └─ protocol.normalize_skill_result()
```

#### SkillResult（`protocol.py`）

```json
{
  "kind": "table | decision | text | empty | ...",
  "text": "...",
  "data": { "rows": [], "columns": [], "plan_summary": {}, "analysis_proposal": {}, "dashboard_middleware": {} },
  "charts": [],
  "kpis": [],
  "chart_plan": {}
}
```

### 2.5 渲染层 (renderers/)

| 文件 | 职责 |
|------|------|
| `chart.py` | `plan_to_option()` → ECharts option；PDF 用 PNG 导出辅助 |
| `kpi.py` | `build_kpi_cards()` |

### 2.6 报表 / PDF (report/)

| 文件 | 职责 |
|------|------|

### 2.7 其他服务

| 文件 | 职责 |
|------|------|
| `memory_service.py` | `format_memory_for_prompt`；`refresh_memory_after_turn`（BackgroundTasks） |
| `trace.py` | `log_event()` → `chatbi_demo.log`（mysql CLI，best-effort） |
| `app_llm.py` | `effective_llm_params()`：env + `admin_llm_settings` + **active Profile** |
| `llm_runtime.py` | LiteLLM 调用封装、fallback 等 |
| `dashboard_overview.py` | `/dashboard/overview` 聚合 KPI 与图表数据 |

### 2.9 路由层 (routes/)

| 路由文件 | 端点（摘要） | 职责 |
|----------|-------------|------|
| `auth_route.py` | `POST /auth/login`、`GET /auth/me` | JWT 登录 |
| `chat_route.py` | `POST /chat`、`POST /abort` | SSE 对话；按 trace_id 中止 |
| `sessions_route.py` | `/sessions` | 会话 CRUD、消息、PDF、suggested_prompts |
| `dashboard_route.py` | `GET /dashboard/overview` | 仪表盘 |
| `admin_db_route.py` | `/db-connections` | 数据源 CRUD |
| `admin_llm_route.py` | `/admin/llm-settings` | 全局 LLM 行 + 生效摘要 |
| `admin_llm_profiles_route.py` | `/admin/llm-profiles` | Profile CRUD、排序、激活、测试连接 |
| `admin_skills_route.py` | `/skills` | SKILL.md 与启用开关 |
| `admin_multi_agents_route.py` | `/admin/multi-agents` | `registry.yaml` |
| `admin_users_route.py` | `/admin/users` | 用户管理 |

---

## 3. 请求完整流程（`/chat`）

```
HTTP POST /chat
    ▼
get_current_user
    ▼
resolve_skill_db_env(db_connection_id)
    ▼
format_memory_for_prompt(user_id)          # CHATBI_MEMORY_DISABLED 可跳过
    ▼
get_session_for_user → insert_message(user)
    ▼
augment_messages_for_upload_followup
    ▼
get_abort_event(trace_id)                  # 本轮可 POST /abort
    ▼
stream_chat(...)
    ├─ multi_agent_runner / react_runner / legacy
    │     ├─ context_window（ReAct/Manager）
    │     ├─ prompt_builder + memory + role_prompt
    │     ├─ planner → executor → observation → formatter
    │     └─ 轮询 is_aborted → ChatAbortedError
    ▼
EventSourceResponse (SSE)
    ├─ thinking / text / chart / kpi_cards
    ├─ plan_summary / analysis_proposal / dashboard_ready
    ├─ error
    └─ done
    ▼ finally:
    ├─ insert_message(assistant, payload_json)
    ├─ touch_session
    ├─ clear_abort(trace_id)
    └─ background_tasks: refresh_memory_after_turn
```

客户端断开或中止时，SSE 消费循环停止拉流（`sse.abort_stop_consumer` 等 trace）。

---

## 4. 关键数据模型

```
app_user
  id, username, password_hash, role, is_active, created_at

app_chat_session
  id, title, user_id, created_at, updated_at

app_chat_message
  id, session_id, role, content, payload_json
  payload_json: thinking, chart, kpiCards, planSummary,
                analysisProposal, dashboardReady, error

app_user_memory
  user_id, kind (session_summary | long_term), title, content,
  source_session_id, updated_at

admin_db_connection
  id, name, host, port, credentials, database_name, is_default, ...

admin_llm_settings
  id=1, model, api_base, api_key, active_profile_id, ...

admin_llm_model_profile
  id, display_name, model, api_base, api_key, sort_order,
  health_status, ...

admin_skill_registry
  skill_slug, enabled
```

---

## 5. Agent 提示词架构

### Legacy

`AGENT_SYSTEM_INSTRUCTION` + `build_system_prompt()` → 可用 Skill 列表（含元数据摘录）。

### ReAct（默认）

`AGENT_REACT_INSTRUCTION` + `SKILL_SELECTION_HINT` + `build_react_system_prompt()`；每步 JSON：`call_skill` | `finish` | `ask`。

### 多专线子 Agent

`prompt_subagent.build_subagent_system_prompt()`：专线 `role_prompt` + 限定 Skill 子集。

叠加顺序：**memory_block → role_prompt（若有）→ 全局指令与 Skill 目录**。

---

## 6. Skill 与多 Agent registry

```
skills/
├── chatbi-semantic-query/、chatbi-comparison/、chatbi-file-ingestion/
├── chatbi-auto-analysis/          # 上传表指标提案与采纳看板
├── chatbi-decision-advisor/、…（共 11 个 SKILL.md）
├── _shared/                       # DB、trace、协议工具
└── _agents/registry.yaml          # 六条专线：upload_analyst、demo_query、
                                   # period_compare、viz_board、semantic_config、
                                   # business_advisor
```

### 子进程隔离

```
Main Process                    Subprocess
┌──────────────────┐            ┌──────────────────┐
│ executor.py      │ ──env──▶   │ skills/.../scripts/*.py
│                  │ ◀──JSON──  │ （只读 business DB）  │
└──────────────────┘            └──────────────────┘
```

---

## 7. 核心技术栈

| 类别 | 技术 |
|------|------|
| Web | FastAPI + Starlette |
| LLM | LiteLLM（OpenAI-compatible） |
| 数据库 | MySQL 8.0 |
| 认证 | JWT + bcrypt |
| 流式 | SSE (`sse_starlette`) |
| 图表 | ECharts（前端）/ matplotlib（PDF） |
| PDF | WeasyPrint + ReportLab |
| 追踪 | MySQL `log` |

---

## 8. 架构设计要点

1. **Skill 子进程隔离**：主进程通过 env 注入 DB；问数/决策脚本仅 `SELECT`（别名 Skill 写受控表）。
2. **ReAct 默认**：Observation 回灌 + `CHATBI_AGENT_MAX_STEPS` 上限；Legacy 与复合双步链仍可用。
3. **三级记忆**：`app_chat_message` → `session_summary` → `long_term`；可 `CHATBI_MEMORY_DISABLED` 关闭。
4. **单库结构**：`chatbi_demo` 承载业务、应用、管理前缀表和链路日志；后端启动时按 `CHATBI_SEED_USERS` 幂等写入 `app_user`。
5. **SSE 类型扩展**：除 text/chart/kpi 外，支持上传分析的 `analysis_proposal`、`dashboard_ready` 与 `plan_summary`。
6. **多 Agent**：Manager 多轮规划 + **顺序**执行专线子任务 + 汇总；上传路径/采纳线索约束路由。
7. **可中止**：`abort_state` + `/abort` + 前端 `AbortSignal`。
8. **上下文窗口**：`context_window` 减少无关历史对 Skill 选用的干扰。
9. **LLM 配置**：env 默认 &lt; `admin_llm_settings` &lt; **active `admin_llm_model_profile`**（管理页切换）。
10. **Skill 选用**：Prompt 元数据 + 专线边界；**无执行前 validator**（已移除 `skill_call_validator`）。

---

## 9. 相关文档

| 文档 | 内容 |
|------|------|
| [guide/tech-guide.md](guide/tech-guide.md) | Agent 分支、记忆、中止、上传中间件 |
| [guide/user-guide.md](guide/user-guide.md) | 页面与操作说明 |
| [architecture/README.md](architecture/README.md) | 分层与禁止跨界 |
| [design/agent-runtime.md](design/agent-runtime.md) | ReAct / Legacy 验收清单 |
| [testing/README.md](testing/README.md) | `scripts/run_tests.py` 套件 |
