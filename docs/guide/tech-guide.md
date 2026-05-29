# ChatBI 技术实现指南

本文面向需要阅读代码或扩展系统的开发者，说明 **Agent 编排、Prompt 拼装、记忆、存储与 Skill 调用** 的实现要点。与 [docs/architecture/README.md](../architecture/README.md) 互补；面向功能与界面的说明见 [user-guide.md](user-guide.md)。

---

## 1. 总入口：`stream_chat` 的分支

后端统一入口为 [`backend/agent/runner.py`](../../backend/agent/runner.py) 中的 `stream_chat`：

```text
multi_agents == True
  → stream_chat_multi_agent（多专线编排）

multi_agents == False 且 CHATBI_AGENT_REACT 非关闭
  → stream_chat_react（ReAct 多步）

否则
  → _stream_chat_legacy（Legacy：单次 JSON 计划 + 可选双步链）
```

环境变量：`CHATBI_AGENT_REACT` 默认开启（`0`/`false`/`no`/`off` 走 Legacy）；`CHATBI_AGENT_MAX_STEPS` 控制 ReAct 最大轮数（默认 `8`，至少 2 才能完成「call_skill + finish」）。

---

## 2. 「单 Agent」模式：ReAct 与 Legacy

「单 Agent」指前端 **未开启多专线**（`multi_agents=false`）：同一套启用 Skill 列表，由一条管线完成本轮回答。

### 2.1 ReAct（默认）

[`backend/agent/react_runner.py`](../../backend/agent/react_runner.py)：

- 每轮 `call_llm_for_react_step(system_prompt, working)` → JSON，`action` 为 `call_skill`、`finish` 或 `ask`。
- `call_skill`：`run_script` → Observation（[`observation.py`](../../backend/agent/observation.py)）追加到 `working`。
- `finish`：合并工具结果与 `text` / `chart_plan` / `kpi_cards` → [`formatter.stream_result_events`](../../backend/agent/formatter.py)。
- [`intent_guard`](../../backend/agent/intent_guard.py)：寒暄等短路，不调用 Skill。
- 进入 LLM 前，会话消息经 [`build_react_context`](../../backend/agent/context_window.py) 做滑动窗口与摘要注入（见 §4.4）。

### 2.2 Legacy

[`_stream_chat_legacy`](../../backend/agent/runner.py)：

- 单次 `call_llm_for_plan` → 执行一步；若命中查询+决策复合意图，则 `chatbi-semantic-query` → `chatbi-decision-advisor` 双步链。

### 2.3 Specialist

[`stream_specialist`](../../backend/agent/runner.py) 将 Skill 列表限定为子集，走 ReAct 或 Legacy；多专线下每子任务调用一次，`messages` 由 [`build_subtask_messages`](../../backend/agent/multi_agent_messages.py) 构造，系统提示使用 [`prompt_subagent`](../../backend/agent/prompt_subagent.py)。

---

## 3. Multi-Agent（多专线）模式

实现：[`multi_agent_runner.py`](../../backend/agent/multi_agent_runner.py)、[`multi_agent_manager.py`](../../backend/agent/multi_agent_manager.py)。

### 3.1 流程概览

1. **Manager 规划（可多轮）**：`call_manager_plan_llm` 读 [`skills/_agents/registry.yaml`](../../skills/_agents/registry.yaml)；每轮 JSON 含 `user_intent_summary`、`decomposition_reason`、`tasks`、`finalize_after_this_batch`（缺省 true）。第 2 轮起附带已完成子任务 digest。上限：`max_manager_rounds`（registry / 管理页 1–8）与 `max_agents_per_round`（每轮子任务数）。
2. **子任务执行**：拓扑序 → `build_subtask_messages` → `stream_specialist(..., subagent_mode=True)`；子任务流式循环内轮询中止（§9）。
3. **汇总**：`blocks` 累积；若中间命中 `chatbi-auto-analysis` 结构化中间件可短路；否则 [`call_summarize_llm`](../../backend/agent/multi_agent_summarize.py)。
4. **回退**：首轮规划无效或 `tasks` 为空 → `stream_chat(..., multi_agents=False)`；多轮后仍无 block 亦降级。

Manager 提示会注入**上传路径、采纳、上传提案**等会话线索，并约束各专线 Skill 边界（与 registry `role_prompt` 一致）。

### 3.2 默认 registry 专线

| id | 主要 skills | 职责 |
|----|-------------|------|
| `upload_analyst` | file-ingestion, auto-analysis | 上传路径分析，禁止用 semantic-query 代替 |
| `demo_query` | semantic-query, database-overview, semantic-processing, metric-explainer | 演示库问数、概览、澄清、指标解释 |
| `period_compare` | comparison | 环比；Observation 含 `comparison_period` 时需对照用户原述 |
| `viz_board` | chart-recommendation, dashboard-orchestration | 有数据后的图表/看板编排 |
| `semantic_config` | alias-manager | 别名写入 |
| `business_advisor` | decision-advisor | 经营建议，缺数据时 finish 说明需先问数 |

### 3.3 与单 Agent 的差异

| 维度 | 单 Agent | Multi-Agent |
|------|-----------|-------------|
| Skill 可见范围 | 全局启用 Skill | 专线 slug ∩ 启用 Skill |
| System 前缀 | memory（可选） | memory + 专线 `role_prompt` |
| LLM 次数 | ReAct 多轮或 Legacy | Manager 多轮 + 子管线 + 汇总 |
| 图表/KPI | 最后 Skill + plan | 常继承最后子任务 `last_result`，汇总覆盖 text |

---

## 4. Prompt 如何组合

### 4.1 System Prompt

[`build_system_prompt` / `build_react_system_prompt`](../../backend/agent/prompt_builder.py)：

1. `AGENT_*_INSTRUCTION`（上传优先 file-ingestion → auto-analysis 等规则）。
2. **可用 Skill**：frontmatter + 正文节选（Workflow、Commands、Safety 等）。
3. 叠加顺序（[`react_runner`](../../backend/agent/react_runner.py) / legacy 一致）：
   - `memory_block`（若有）→ 最外
   - `role_prompt`（专线，若有）
   - 全局指令 + Skill 目录

### 4.2 对话消息（messages）

[`chat_route.py`](../../backend/routes/chat_route.py)：

- 有 `session_id`：[`list_messages_for_llm`](../../backend/session_repo.py) + 本轮用户句。
- 无 session：请求体 `history` + `message`。
- **上传跟进**：[`augment_messages_for_upload_followup`](../../backend/agent/upload_context.py)。

ReAct / Manager 在送入 Planner 前还会经 **context_window** 压缩（§4.4），避免无关历史干扰 Skill 选用。

### 4.3 发给 Planner 的 messages

[`planner.py`](../../backend/agent/planner.py)：system + 上述 messages + 固定 user 尾句（要求只输出 JSON）。ReAct 用 `working` 副本追加 assistant JSON 与 Observation。

### 4.4 上下文滑动窗口

[`context_window.py`](../../backend/agent/context_window.py)：

- `ConversationContextBuilder`：最近 N 轮 + 会话摘要（`list_recent_session_summaries`）+ 按当前问句关键词检索的历史片段。
- `build_react_context` / `build_manager_context`：输出注入 system 或 user 侧的「压缩上下文」块，与 `list_messages_for_llm` 全量历史配合使用。
- 上传路径、技能相关关键词会提高片段保留权重。

### 4.5 Skill 元数据与选用（无执行前校验）

[`prompt_builder._skills_markdown_lines`](../../backend/agent/prompt_builder.py) 将每个 Skill 的 YAML frontmatter 注入 System Prompt：

- `trigger_conditions` → **选用时机**
- `when_not_to_use` → **不要用**
- `required_context` → **必备上下文**

并附加 `SKILL_SELECTION_HINT`，要求 `call_skill` 前对照上述条目。

**注意**：仓库已**移除** `skill_call_validator` 及 `validator_requires`；不会在执行脚本前做硬拦截。纠错依赖 Observation、`role_prompt`、Manager 路由与模型下一轮改选 Skill。

---

## 5. 长短期记忆

[`memory_service.py`](../../backend/memory_service.py) + [`memory_repo.py`](../../backend/memory_repo.py)，表 `chatbi_app_user_memory`（默认库 `chatbi_demo`）。

- **读**：`format_memory_for_prompt` → long_term + session_summary；`CHATBI_MEMORY_DISABLED` 时跳过。
- **写**：SSE 结束且助手消息落库后，`BackgroundTasks` 调用 `refresh_memory_after_turn`（会话摘要 + 合并长期偏好）。
- **推荐追问**：`suggested_prompts_for_user` 用近期摘要 title → `GET /sessions`。

---

## 6. 数据库与数据分布

[`database/init.sql`](../../database/init.sql)：

| 位置 | 用途 |
|------|------|
| `chatbi_demo` | 业务事实表、语义层、`chatbi_app_*`、`chatbi_admin_*` |
| `chatbi_local_logs` | `chatbi_logs_trace_log`（trace-id 串联） |

**Compose 默认**：
- `docker-compose.dev.yml` 与 `docker-compose.yml` 都将 `chatbi_demo` 放到 `demo-mysql` named volume；日志库改走独立 `log-mysql`，宿主机端口 **33067**。
- 宿主机直连主业务库端口分别为 **3308**（dev）和 **3307**（prod）。

宿主机本地运行后端时，默认直接沿用 `CHATBI_DB_*` 作为业务演示库，`CHATBI_LOG_DB_*` 指向独立日志库。

---

## 7. 用户上传文件

### 7.1 存储

[`POST /upload`](../../backend/main.py) → `/tmp/chatbi-uploads/{uuid}_{stem}{ext}`，返回 `server_path`。

### 7.2 进入 Skill

Prompt 要求上传路径优先 `chatbi-file-ingestion`；有 rows 后探索/采纳走 `chatbi-auto-analysis`。`upload_context` 在跟进轮自动补提示。

### 7.3 上传分析与 SSE 中间件

[`chatbi-auto-analysis`](../../skills/chatbi-auto-analysis/SKILL.md)：profile → 指标提案 → 用户确认 → 确定性执行 → `dashboard_middleware`。

[`chat_route.py`](../../backend/routes/chat_route.py) 将 Skill/formatter 事件映射为 SSE 并落库：

| SSE type | 前端字段 | 含义 |
|----------|----------|------|
| `analysis_proposal` | `analysisProposal` | 指标提案 Markdown + `proposed_metrics` |
| `dashboard_ready` | `dashboardReady` | 采纳后看板 JSON（KPI、charts、table） |

Multi-Agent 在 [`multi_agent_runner`](../../backend/agent/multi_agent_runner.py) 可对 auto-analysis 中间件**短路**，直接向前端推送上述结构化结果。

---

## 8. Skill 一览

目录名 = `skill` slug；启用过滤：[`scan_skills_enabled`](../../backend/agent/prompt_builder.py) + `chatbi_admin_skill_registry`。

| Skill slug | 作用（摘要） | 典型用法 |
|------------|----------------|----------|
| `chatbi-semantic-query` | 语义层约束只读 SQL + 图表计划 | 问数、排行、趋势 |
| `chatbi-semantic-processing` | 意图/槽位澄清 | 含糊问法 |
| `chatbi-database-overview` | 表/字段概览 | 「有哪些表」 |
| `chatbi-metric-explainer` | 指标口径 | 「销售额怎么算」 |
| `chatbi-comparison` | 环比/对比 | 「环比」「相较于」；Observation 可含 `comparison_period` |
| `chatbi-decision-advisor` | 经营建议 | 单独或 Legacy 双步链第二步 |
| `chatbi-alias-manager` | 别名写入 | 用户明确要求登记 |
| `chatbi-file-ingestion` | 上传 CSV/XLSX 校验/预览 | 路径含 `chatbi-uploads` |
| `chatbi-auto-analysis` | 上传表指标提案与采纳看板 | ingestion 之后 |
| `chatbi-chart-recommendation` | 图表类型推荐 | 已有数据形状 |
| `chatbi-dashboard-orchestration` | 看板编排叙事 | 演示库 dashboard 意图 |

Agent 不直接执行 SQL：`executor` 子进程 `--json` → SkillResult → formatter / renderers → SSE。

---

## 9. 对话中止

- **状态**：[`abort_state.py`](../../backend/agent/abort_state.py) 按 `trace_id` 维护 `asyncio.Event`。
- **接口**：`POST /abort`（[`chat_route`](../../backend/routes/chat_route.py)）设置中止标志。
- **协作**：[`abort_async.await_with_abort`](../../backend/agent/abort_async.py) 包装 LLM 调用；ReAct / Multi-Agent / executor 子进程轮询 `is_aborted`；触发 `ChatAbortedError` 后 yield「用户中止了查询」类 thinking。
- **前端**：[`abortChat`](../../frontend/src/api/client.ts) + `fetch` 的 `AbortSignal`；[`useChat.abort`](../../frontend/src/hooks/useChat.ts)。
- **断连**：SSE 消费循环在客户端断开或中止时停止拉流并 `clear_abort`。

---

## 10. 与其它文档的交叉引用

| 主题 | 文档 |
|------|------|
| 模块分层与禁止事项 | [architecture/README.md](../architecture/README.md) |
| ReAct / Legacy 验收 | [design/agent-runtime.md](../design/agent-runtime.md) |
| SkillResult / SSE | `backend/agent/protocol.py`、`formatter.py` |
| 环境变量 | `.env.example`、`backend/config.py` |
| 测试套件 | [testing/README.md](../testing/README.md)、`scripts/run_tests.py` |

---

## 11. 修订记录

重大行为变更（默认 ReAct、registry 结构、移除 skill_call_validator、日志库 compose 双库等）请同步更新本文。
