# ChatBI 技术实现指南

本文面向需要阅读代码或扩展系统的开发者，说明 **Agent 编排、Prompt 拼装、记忆、存储与 Skill 调用** 的实现要点。与 [`docs/architecture/README.md`](architecture/README.md) 互补；面向功能与界面的说明见 [`docs/user-guide.md`](user-guide.md)。

---

## 1. 总入口：`stream_chat` 的分支

后端统一入口为 [`backend/agent/runner.py`](../backend/agent/runner.py) 中的 `stream_chat`。分支顺序如下：

```text
multi_agents == True
  → stream_chat_multi_agent（多专线编排）

multi_agents == False 且 CHATBI_AGENT_REACT 非关闭
  → stream_chat_react（ReAct 多步）

否则
  → _stream_chat_legacy（Legacy：单次 JSON 计划 + 可选双步链）
```

环境变量：`CHATBI_AGENT_REACT` 默认为开启（`0`/`false`/`no`/`off` 则走 Legacy）；`CHATBI_AGENT_MAX_STEPS` 控制 ReAct 最大轮数（默认 `8`，须 ≥2 才能完成「一次 call_skill + 一次 finish」）。

---

## 2. 「单 Agent」模式：ReAct 与 Legacy

这里的「单 Agent」指 **未开启前端「多专线协作」**（`multi_agents=false`）时的路径：同一套 Skill 列表（经启用表过滤），由 **一条执行管线** 完成本轮回答。

### 2.1 ReAct（默认）

实现：[`backend/agent/react_runner.py`](../backend/agent/react_runner.py)。

- **循环**：最多 `agent_max_steps` 次；每轮调用 `call_llm_for_react_step(system_prompt, working)`，模型返回 JSON，`action` 为 `call_skill` 或 `finish`。
- **`call_skill`**：定位 Skill → `run_script` 执行子进程 → 将助手 JSON 摘要与 **Observation**（[`backend/agent/observation.py`](../backend/agent/observation.py) 对结果的摘要）追加到 `working` 对话列表，进入下一轮。
- **`finish`**：将最后一次工具结果与模型给出的 `text` / `chart_plan` / `kpi_cards` 合并，经 [`formatter.stream_result_events`](../backend/agent/formatter.py) 转成 SSE（text / chart / kpi_cards）。
- **短路**：[`intent_guard`](../backend/agent/intent_guard.py) 判定为寒暄等简单话语时，不调用 Skill，直接返回固定口吻文本。

### 2.2 Legacy（关闭 ReAct 时）

实现：[`backend/agent/runner.py`](../backend/agent/runner.py) 中 `_stream_chat_legacy`。

- **单次规划**：`call_llm_for_plan(system_prompt, messages)` 返回一整份 JSON 计划（含 `skill`、`skill_args`、`chart_plan` 等）。
- **执行**：默认执行一步；若用户问题同时命中「查询类」与「决策建议类」正则（[`_is_query_plus_decision`](../backend/agent/runner.py)），则 `_build_steps` 拆成两步：**先 `chatbi-semantic-query`，再 `chatbi-decision-advisor`**。第二步会把第一步结果推断出的主维度拼进决策 Skill 的参数（`_infer_primary_dimension`）。
- **渲染**：每步结束后同样走 `stream_result_events`。

### 2.3 Specialist（过滤 Skill 列表的同一条管线）

[`stream_specialist`](../backend/agent/runner.py) 把 **Skill 文档列表** 限定为子集（仅传入的 `skill_docs`），然后根据配置走 **ReAct 或 Legacy**。多专线（Manager）模式下每个子任务调用一次 `stream_specialist`，使用 **子 agent 专用** ReAct/Legacy 系统提示（仅列出该专线技能）；`messages` 由 [`build_subtask_messages`](../backend/agent/multi_agent_messages.py) 按交办与用户原述构造。

---

## 3. Multi-Agent（多专线）模式如何运行

实现：[`backend/agent/multi_agent_runner.py`](../backend/agent/multi_agent_runner.py)。

### 3.1 流程概览

1. **Manager 规划（可多轮）**：[`call_manager_plan_llm`](../backend/agent/multi_agent_manager.py) 读取 registry 专线与技能；每轮输出 JSON：`user_intent_summary`、`decomposition_reason`、`tasks`、`finalize_after_this_batch`（本批后是否仍要下一轮规划；缺省 true）。首轮仅用户对话；第 2 轮起附带已完成子任务 digest。`max_manager_rounds` 与 `max_agents_per_round` 见 [`skills/_agents/registry.yaml`](../skills/_agents/registry.yaml)。
2. **子任务顺序执行**：每轮内对每个子任务（拓扑序）→ `build_subtask_messages` → `stream_specialist(..., subagent_mode=True)`。
3. **跨轮汇总**：各轮结果累积进 `blocks`（含 `round`）；中间可因 `chatbi-auto-analysis` 中间件短路；否则 `call_summarize_llm` 汇总。
4. **回退**：首轮规划失败或首轮无有效 `tasks` 则单次 Agent；多轮后仍无 block 亦降级。

### 3.2 与「单 Agent」的差异（要点）

| 维度 | 单 Agent | Multi-Agent |
|------|-----------|-------------|
| Skill 可见范围 | 全局启用 Skill（目录扫描 − `skill_registry` 禁用项） | 每条专线 registry 中的 slug ∩ 启用 Skill |
| System 前缀 | 可选 memory + 无专线 role | 每条专线注入各自的 `role_prompt` |
| LLM 调用次数 | ReAct 多轮或 Legacy 一轮（+ 复合意图第二步） | 至多 `max_manager_rounds` 次 Manager 规划 + 每轮子任务内子管线 + 汇总 1 次 |
| 最终图表/KPI | 直接来自最后一次 Skill 结果 + 模型 plan | 汇总 LLM 的 plan 覆盖 text，结构化结果常继承 **最后一次子任务** 的 `last_result` |

---

## 4. 一轮查询中 Prompt 如何组合

### 4.1 System Prompt 的拼装

核心函数：[`build_system_prompt`](../backend/agent/prompt_builder.py) / [`build_react_system_prompt`](../backend/agent/prompt_builder.py)。

结构：

1. **固定指令**：`AGENT_SYSTEM_INSTRUCTION`（Legacy）或 `AGENT_REACT_INSTRUCTION`（ReAct），定义 JSON 字段、`call_skill`/`finish` 语义、上传文件优先规则、可视化约束等。
2. **可用 Skill**：对每个启用的 `skills/*/SKILL.md`，解析 frontmatter，并从正文 **按需摘录** 小节（Workflow/工作流、Commands/常用命令、Safety/安全边界、可视化指导等），拼成 Markdown 块。

Runner 中的叠加顺序（[`react_runner`](../backend/agent/react_runner.py) 与 [`_stream_chat_legacy`](../backend/agent/runner.py) 一致）：

1. `system_prompt = build_*_system_prompt(skills)` → 得到「全局指令 + 可用 Skill 摘录」。
2. 若有 `role_prompt`：`system_prompt = role_prompt + "\n\n" + system_prompt`（专线角色在前）。
3. 若有 `memory_block`：`system_prompt = memory_block + "\n\n" + system_prompt`（**记忆块在最外层**，最先被模型读到）。

即最终字符串顺序为：**记忆 → 专线角色（若有）→ 全局 Agent 指令与 Skill 目录**。

### 4.2 对话消息（messages）

来源：[`backend/routes/chat_route.py`](../backend/routes/chat_route.py)。

- 若带 `session_id`：从数据库读取该会话历史 [`list_messages_for_llm`](../backend/session_repo.py)，再追加本轮用户句。
- 否则：使用请求体中的 `history` + 本轮 `message`。

后续两处预处理（按顺序）：

1. **Vision**：[`enrich_last_user_message_with_vision`](../backend/vision/chart_table_extract.py) — 若最新消息含上传图像路径且未禁用视觉，会用配置的视觉模型抽取表格/文本并写入用户消息内容（具体条件见模块内逻辑）。
2. **上传跟进**：[`augment_messages_for_upload_followup`](../backend/agent/upload_context.py) — 若历史中出现过 `/tmp/chatbi-uploads/` 路径，且本轮用户继续追问「分析/画图」等，则在 **最新用户消息前** 拼接硬性上下文提示，引导使用 `chatbi-file-ingestion`，避免误走演示库 `chatbi-semantic-query`。

### 4.3 发给 Planner 的完整 messages

实现：[`backend/agent/planner.py`](../backend/agent/planner.py)。

- **ReAct**：`[{"role":"system","content": system_prompt}, *messages, {"role":"user","content":"请只输出一个 JSON 对象作为本步决策（必须包含 action 字段），不要输出其它文字。"}]`
- **Legacy**：`[{"role":"system","content": system_prompt}, *messages, {"role":"user","content":"请以 JSON 格式输出你的行动计划。"}]`

其中 `messages` 为上述会话数组；ReAct 内部用 **working** 副本不断追加「助手 JSON + Observation」，多轮推理。

**注意**：记忆内容通过 **System** 侧的 `memory_block` 注入，不是额外一条独立的「记忆」角色消息。

---

## 5. 长短期记忆机制

实现：[`backend/memory_service.py`](../backend/memory_service.py) + [`backend/memory_repo.py`](../backend/memory_repo.py)，默认表为 [`chatbi_app_user_memory`](../database/init.sql)（库 `chatbi_demo`，除非显式设置 `CHATBI_APP_DB_*` 拆库）。

### 5.1 注入（读）

[`format_memory_for_prompt(user_id)`](../backend/memory_service.py)：

- 若 `CHATBI_MEMORY_DISABLED` 为真，返回空串。
- **长期**：`kind = 'long_term'`，单行文本，概括「用户查询习惯与稳定偏好」。
- **短期（近期会话摘要）**：`kind = 'session_summary'`，取最近若干条，格式化为「## 近期会话摘要」列表。

拼接后再附一句免责声明：业务事实以工具查询为准。

该字符串在 `/chat` 中作为 `memory_block` 传入 `stream_chat`，见上文 System 拼装顺序。

### 5.2 刷新（写）

在 SSE **结束且助手消息成功落库** 后，通过 FastAPI `BackgroundTasks` 异步调用 [`refresh_memory_after_turn`](../backend/memory_service.py)：

1. 用 LLM 根据本轮「用户问题 + 助手回答摘录」生成 **会话级摘要**，写入 `session_summary`（按 `source_session_id` 先删后插），并 `trim_session_summaries` 控制条数。
2. 再拉取近期多条摘要与旧长期记忆，合并生成新的 **长期偏好文本**，`upsert_long_term`。

失败仅记 trace，不阻塞主链路。

### 5.3 与会话列表的「推荐追问」

[`suggested_prompts_for_user`](../backend/memory_repo.py) 使用近期 `session_summary` 的 **title** 字段作为快捷 chip 文案来源之一（与 [`GET /sessions`](../backend/routes/sessions_route.py) 返回的 `suggested_prompts` 对应）。

---

## 6. 数据库与数据分布

初始化脚本：[`database/init.sql`](../database/init.sql)。

| 位置 | 用途 |
|------|------|
| `chatbi_demo` | **业务事实表**（`sales_order`、`customer_profile`）+ **语义层**（指标/维度/字段词典/别名 `alias_mapping`/数据源登记等） |
| `chatbi_demo.chatbi_app_*` | **用户**、**会话**、**消息**、**记忆**；可用 `CHATBI_APP_DB_*` 主动拆库 |
| `chatbi_demo.chatbi_admin_*` | **Skill 开关**、**数据源连接**、**LLM 覆盖配置**；可用 `CHATBI_ADMIN_DB_*` 主动拆库 |
| `chatbi_local_logs.chatbi_logs_trace_log` | **链路日志**，trace-id 串联上传、chat、Skill 等；`.env.dev` 默认指向本机 `33067` |

演示业务数据为 2026 年样例订单与客户画像；语义层驱动问数 Skill 的字段约束与别名解析。

---

## 7. 用户上传文件：存放位置与调用链

### 7.1 存储

[`backend/main.py`](../backend/main.py)：`POST /upload`

- 目录：**`/tmp/chatbi-uploads`**（容器内路径；宿主机若挂载则依部署而定）。
- 文件名：`{uuid}_{安全化原始 stem}{后缀}`。
- 允许后缀：`csv` / `xlsx` / `xlsm` / 常见图片（PNG/JPG/WebP）。
- 返回：`server_path`（绝对路径字符串）、`trace_id`、`size` 等。

前端把路径写进用户将要发送的文案，随 `/chat` 一并交给 Agent。

### 7.2 如何进入到 Skill

1. **Prompt 层**：`AGENT_*_INSTRUCTION` 明确要求：若用户针对上传路径分析，应优先 **`chatbi-file-ingestion`**，而非 **`chatbi-semantic-query`** 查演示库。
2. **上下文增强**：跟进轮若未重复敲路径，[`upload_context`](../backend/agent/upload_context.py) 自动注入提示前缀。
3. **执行层**：[`executor.run_script`](../backend/agent/executor.py) 将模型给出的参数传给对应 `skills/<slug>/scripts/` 入口；文件类 Skill 读取 `server_path` 做校验或预览。

图像：先在 chat_route 中做 **Vision 增强**，再进入同一套 Agent；是否启用见环境变量（如 `CHATBI_VISION_DISABLED`）及 [`chart_table_extract`](../backend/vision/chart_table_extract.py)。

---

## 8. Skill 一览与 Agent 如何使用

所有 Skill 均在 `skills/<目录名>/SKILL.md` 注册；**目录名**即 **`skill` 字段使用的 slug**。启用状态默认由 `chatbi_demo.chatbi_admin_skill_registry` 过滤（[`scan_skills_enabled`](../backend/agent/prompt_builder.py)）。

| Skill slug | 作用（摘要） | Agent 侧典型用法 |
|------------|----------------|------------------|
| `chatbi-semantic-query` | 自然语言 → 受语义层约束的只读 SQL，返回表格/结构化结果，并可带 `chart_plan` | 问数、排行、趋势类问题的主要工具 |
| `chatbi-decision-advisor` | 基于查询事实生成经营决策建议（规则 + 指标计算） | 单独调用或与语义查询组成 Legacy 双步链 |
| `chatbi-alias-manager` | 向 `alias_mapping` **插入已验证**别名 | 用户明确要求登记别名时 |
| `chatbi-comparison` | 环比/对比分析（多月中两期对比等） | 环比、对比类措辞 |
| `chatbi-file-ingestion` | 读用户上传 CSV/XLSX，按演示表结构校验/预览（可 `--include-rows`） | 路径含上传目录且用户针对文件分析时 |
| `chatbi-chart-recommendation` | 针对已有数据形状推荐图表类型与 KPI | 「推荐什么图」类问题 |
| `chatbi-dashboard-orchestration` | 基于 dashboard 概览数据生成看板级叙事与可视化建议 | 「生成看板/仪表盘编排」类意图 |
| `chatbi-semantic-processing` | 语义解析 / query intent（供编排或澄清） | Planner 按触发规则选用 |
| `chatbi-metric-explainer` | 指标口径解释类 | 专线 registry 中通常挂在「演示库问数」类子 agent（如 `demo_query`） |

**Agent 本身不执行 SQL**：只产出 JSON 计划 → [`executor`](../backend/agent/executor.py) 找脚本路径、注入数据库连接环境变量（含会话级 `db_connection_id` 解析结果）→ 子进程执行 `--json` → 返回统一 **SkillResult** → [`formatter`](../backend/agent/formatter.py) / [`renderers`](../backend/renderers/) 转为 SSE。

**Skill 文档注入**：`build_*_system_prompt` 只抽取 SKILL.md 中若干小节进入 System Prompt；Planner 仍须只在「可用 Skill」列表中选名。

---

## 9. 与其它文档的交叉引用

| 主题 | 文档 |
|------|------|
| 模块分层与禁止事项 | [`docs/architecture/README.md`](architecture/README.md) |
| ReAct / Legacy 验收清单 | [`docs/design/agent-runtime.md`](design/agent-runtime.md) |
| SkillResult 协议与渲染 | `backend/agent/protocol.py`、`backend/agent/formatter.py` |
| 环境变量 | 根目录 `.env.example`、`backend/config.py` |

---

## 10. 修订记录

重大行为变更（例如默认 ReAct、registry 结构、记忆开关）请同步更新本文或提交说明，避免与线上配置脱节。
