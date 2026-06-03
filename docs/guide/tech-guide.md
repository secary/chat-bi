# ChatBI 技术实现指南

本文面向需要阅读代码或扩展系统的开发者，说明 **Agent 编排、Prompt 拼装、记忆、存储与 Skill 调用** 的实现要点。与 [docs/architecture/README.md](../architecture/README.md) 互补；面向功能与界面的说明见 [user-guide.md](user-guide.md)。

---

## 1. 总入口：`stream_chat` 的分支

后端统一入口为 [`backend/agent/runner.py`](../../backend/agent/runner.py) 中的 `stream_chat`：

```text
multi_agents == "auto"（前端默认）
  → decide_execution_mode(messages)
    ├─ mode == "ask"    → 返回澄清问题
    ├─ mode == "multi"  → stream_chat_multi_agent（多专线编排）
    └─ mode == "single" → 单 Agent

multi_agents == True
  → stream_chat_multi_agent（多专线编排）

multi_agents == False 且 CHATBI_AGENT_REACT 非关闭
  → stream_chat_react（ReAct 多步）

否则
  → _stream_chat_legacy（Legacy：单次 JSON 计划 + 可选双步链）
```

环境变量：`CHATBI_AGENT_REACT` 默认开启（`0`/`false`/`no`/`off` 走 Legacy）；`CHATBI_AGENT_MAX_STEPS` 控制 ReAct 最大轮数（默认 `8`，至少 2 才能完成「call_skill + finish」）。

当前前端聊天页固定发送 `multi_agents="auto"`；是否进入多专线，不再由用户在聊天页手动开关，而是由 [`execution_decider.py`](../../backend/agent/execution_decider.py) 根据本轮消息自动判断。

---

## 2. 「单 Agent」模式：ReAct 与 Legacy

「单 Agent」指本轮请求最终被路由到 **single**：同一套启用 Skill 列表，由一条管线完成本轮回答。来源可能是：

- 显式传入 `multi_agents=false` 或 `"single"`
- `multi_agents="auto"` 时，`decide_execution_mode()` 判定当前问题适合单 Agent

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

进入多专线的前提：本轮请求显式 `multi_agents=true`，或 `multi_agents="auto"` 且 [`decide_execution_mode()`](../../backend/agent/execution_decider.py) 返回 `mode="multi"`。

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

### 3.4 `auto` 智能路由决策

[`decide_execution_mode()`](../../backend/agent/execution_decider.py) 当前采用受控规则：

| 输入特征 | mode | route / 结果 |
|----------|------|--------------|
| 空消息 | `ask` | 要求用户先补充问题 |
| 寒暄、感谢等可跳过 Skill 的消息 | `single` | 直接走单 Agent 文本回复 |
| 纯问数，如“查华东销售额” | `single` | 保留受控 route，如 `demo_query`，但不进入多专线 |
| 纯图表建议、缺少数据目标，如“建议用柱状图还是折线图” | `single` | 不强行查询演示库，由单 Agent 解释或追问 |
| 纯建议、缺少事实范围，如“给我经营建议” | `ask` | 返回澄清，要求补充指标、时间、区域等 |
| 复合目标：问数 + 建议 / 问数 + 图表 / 上传分析 / 跨期 | `multi` | 进入多专线，按 `route_sequence` 顺序执行 |
| 未命中结构化路由 | `single` | 降级为单 Agent |

`route_sequence` 来自 [`multi_agent_intent.py`](../../backend/agent/multi_agent_intent.py) 的受控意图分类，当前主要包括：

- `query_only` → `["demo_query"]`
- `query_then_decide` → `["demo_query", "business_advisor"]`
- `query_then_viz` → `["demo_query", "viz_board"]`
- `query_then_decide_then_viz` → `["demo_query", "business_advisor", "viz_board"]`
- `upload_then_analyze` → `["upload_analyst"]`
- `upload_then_viz` → `["upload_analyst", "viz_board"]`
- `period_compare` → `["period_compare"]`

### 3.5 统一决策路径总表

下面这张表把当前分散在 `execution_decider.py`、`multi_agent_intent.py`、`multi_agent_runner.py` 的规则收敛到一处，按“输入特征 → `decision.mode` → `route_sequence` → 执行去向 / fallback”阅读即可。

| 输入特征 | `intent_type` / 路由信号 | `decision.mode` | `route_sequence` | 实际执行去向 | `ask` / fallback |
|----------|--------------------------|-----------------|------------------|--------------|------------------|
| 空消息 | 无 | `ask` | `[]` | 不进入单 Agent / 多专线；直接由 `runner._stream_ask_for_clarification()` 返回澄清 | 提示用户先补充问题 |
| 寒暄、感谢、无需 Skill 的短消息 | `should_skip_skill_for_message == true` | `single` | `[]` | `stream_chat_react()` 或 `_stream_chat_legacy()`，通常直接文字回复 | 无 |
| 未命中受控业务路由 | `classify_multi_agent_intent() == None` | `single` | `[]` | 单 Agent 执行 | 记录 `intent_unmatched` 风险标记 |
| 纯图表建议但没有数据目标，如“建议用柱状图还是折线图” | `classify_multi_agent_intent() == None` | `single` | `[]` | 单 Agent 执行；不强行补 `demo_query` | 无 |
| 纯问数，如“查华东销售额” | `query_only` | `single` | `["demo_query"]` | 单 Agent 执行；`route_sequence` 只作为审计 / 理解线索保留 | 无 |
| 只要建议但没事实范围，如“给我经营建议” | `routes == ["business_advisor"]` | `ask` | `["business_advisor"]` | 不进入多专线 | 返回澄清，要求补充指标、时间、区域等事实范围 |
| 问数后给建议 | `query_then_decide` | `multi` | `["demo_query", "business_advisor"]` | 第 1 轮 `build_initial_plan_from_intent()` 先派 `demo_query`；后续 `build_next_plan_from_intent()` 切到 `business_advisor` | 若首轮任务校验失败，回退单 Agent；若最终无 `all_blocks`，也回退单 Agent |
| 问数后出图 | `query_then_viz` | `multi` | `["demo_query", "viz_board"]` | 先问数，再切图表 / 看板专线 | 同上 |
| 问数后给建议再出图 | `query_then_decide_then_viz` | `multi` | `["demo_query", "business_advisor", "viz_board"]` | 每轮完成一个 route，直到 `_route_objective_completed()` 判断全部 route 已完成 | 同上 |
| 上传文件后分析 | `upload_then_analyze` | `multi` | `["upload_analyst"]` | 直接进入上传分析专线 | 若中途命中 auto-analysis 结构化中间件，可短路直接出结果 |
| 上传文件后分析再出图 | `upload_then_viz` | `multi` | `["upload_analyst", "viz_board"]` | 先上传分析，再切换到图表 / 看板专线 | 同上 |
| 跨期对比，如环比 / 同比 | `period_compare` | `multi` | `["period_compare"]` | 直接进入跨期对比专线 | 若校验失败或无 block，回退单 Agent |

#### 决策链路对应实现

1. **判模式**：[`decide_execution_mode()`](../../backend/agent/execution_decider.py) 决定 `single` / `multi` / `ask`。
2. **判 route**：[`classify_multi_agent_intent()`](../../backend/agent/multi_agent_intent.py) 产出 `intent_type`、`current_route`、`route_sequence`。
3. **首轮任务**：[`build_initial_plan_from_intent()`](../../backend/agent/multi_agent_intent.py) 把 `route_sequence[0]` 转成第 1 轮任务。
4. **后续切线**：[`build_next_plan_from_intent()`](../../backend/agent/multi_agent_intent.py) 根据 `completed_agents` 依次切到下一条专线；切线时 [`multi_agent_runner.py`](../../backend/agent/multi_agent_runner.py) 会记录 `route_transition_selected`。
5. **完成判定**：[`_route_objective_completed()`](../../backend/agent/multi_agent_runner.py) 判断受控 `route_sequence` 是否全部完成；完成时记录 `route_objective_completed`。
6. **失败与回退**：
   - 首轮 `validate_and_order_tasks()` 失败：立即 `fallback_single`
   - 多轮执行后 `all_blocks` 仍为空：`fallback_single`
   - 纯建议但无事实：不回退，直接 `ask`

#### 读日志时最有用的事件

- `agent.harness.execution_decision_selected`：本轮为什么被判到 `single` / `multi` / `ask`
- `agent.harness.route_intent_classified`：命中了哪个 `intent_type` 与 `route_sequence`
- `agent.harness.route_transition_selected`：多专线从上一条 route 切到下一条 route
- `agent.harness.route_objective_completed`：受控 route 序列已经跑完
- `agent.multi.fallback_single`：多专线未形成有效任务或无有效 block，降级为单 Agent

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

[`memory_service.py`](../../backend/memory_service.py) + [`memory_repo.py`](../../backend/memory_repo.py)，表 `app_user_memory`（默认库 `chatbi_demo`）。

- **读**：`format_memory_for_prompt` → long_term + session_summary；`CHATBI_MEMORY_DISABLED` 时跳过。
- **写**：SSE 结束且助手消息落库后，`BackgroundTasks` 调用 `refresh_memory_after_turn`（会话摘要 + 合并长期偏好）。
- **推荐追问**：`suggested_prompts_for_user` 用近期摘要 title → `GET /sessions`。

---

## 6. 数据库与数据分布

[`database/init.sql`](../../database/init.sql)：

| 位置 | 用途 |
|------|------|
| `chatbi_demo` | 业务事实表、语义层、`app_user`、`app_chat_session`、`app_chat_message`、`app_user_memory`、`admin_db_connection`、`admin_llm_settings`、`admin_llm_model_profile`、`admin_skill_registry`、`log`（trace-id 串联） |

**Compose 默认**：
- `docker-compose.dev.yml` 只启动开发 MySQL；`docker-compose.prod.yml` 启动生产式 MySQL 与一体应用容器，并初始化 `chatbi_demo` 一个库。
- 宿主机直连 MySQL 端口分别为 **33067**（dev）和 **3307**（prod）。

宿主机本地运行后端时，日志连接默认复用 `CHATBI_DB_HOST/PORT/USER/PASSWORD/NAME`；仅在需要拆分日志库时设置 `CHATBI_LOG_DB_NAME`。

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

目录名 = `skill` slug；启用过滤：[`scan_skills_enabled`](../../backend/agent/prompt_builder.py) + `admin_skill_registry`。

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
