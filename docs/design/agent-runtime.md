# Agent 运行时设计与验收

本文描述 ChatBI Agent 的两种运行时模式，并包含后续可选的 ReAct 增强设计。

环境变量（参见根目录 [`.env.example`](../../.env.example)）：

- **`CHATBI_AGENT_REACT`**：默认开启（`1` / 非 `0` / 非 `false`）。关闭时使用 Legacy 单次规划路径。
- **`CHATBI_AGENT_MAX_STEPS`**：ReAct 模式下每则用户消息允许的 LLM 调用次数上限（默认 `8`）。一次典型的「先调用 Skill、再收尾」至少需要 **2** 轮 LLM。

---

## A. ReAct 模式（默认）

**定性**：「Thought（JSON）→ Action（Skill）→ Observation（摘要回灌）→ … → finish」的多轮闭环。实现位置：[`stream_chat_react`](../../backend/agent/react_runner.py)，每轮调用 [`call_llm_for_react_step`](../../backend/agent/planner.py)。

**验收清单**

- [ ] 每轮模型输出 JSON，包含 `action`：`call_skill` 或 `finish`。
- [ ] `call_skill` 时执行至多一次 [`run_script`](../../backend/agent/executor.py)，随后将 [`summarize_observation`](../../backend/agent/observation.py) 追加为 user 消息并继续下一轮 LLM。
- [ ] `finish` 时合并最后一次工具结果与 `text` / `chart_plan`，经 [`stream_result_events`](../../backend/agent/formatter.py) 输出 SSE。
- [ ] 达到 `CHATBI_AGENT_MAX_STEPS` 仍未 `finish` 时，有明确的兜底文案或最后一次工具结果展示。
- [ ] [`tests/test_react_runner.py`](../../tests/test_react_runner.py) 通过。

---

## B. Legacy 模式（`CHATBI_AGENT_REACT=0`）

**定性**：「单次 JSON 规划 → 至多一次 Skill → SSE」的 Plan-and-Execute，不做多轮 LLM 回灌。

**验收清单**

- [ ] [`call_llm_for_plan`](../../backend/agent/planner.py) 每次请求仅调用一次，产出含 `skill`、`skill_args`、`text`、`chart_plan`、`kpi_cards`、`steps` 的 JSON 计划。
- [ ] 当 `skill` 有效时，[`run_script`](../../backend/agent/executor.py) 最多调用一次；`skill` 为 null 时不执行脚本。
- [ ] Skill 结果不再次送入 LLM，直接进入 [`stream_result_events`](../../backend/agent/formatter.py)。
- [ ] 每次请求扫描 `skills/*/SKILL.md`，[`build_system_prompt`](../../backend/agent/prompt_builder.py) 包含当前可用 Skill 列表。
- [ ] [`tests/test_agent_runner_contract.py`](../../tests/test_agent_runner_contract.py) 通过。

---

## C. ReAct 后续可选增强

已落地的多轮循环无需 LangGraph，后续可按需扩展：

### Observation 格式

对脚本输出做摘要后回灌，避免大表撑爆上下文：

```json
{
  "skill": "chatbi-semantic-query",
  "ok": true,
  "kind": "table",
  "row_count": 12,
  "columns": ["区域", "销售额"],
  "sample_rows": [{"区域": "华东", "销售额": "100"}],
  "error": null
}
```

失败时：`ok: false`，`error` 为脚本 stderr 或归一化错误信息。

### Planner 实现路径

1. **保留 JSON 计划 + 外层循环**（当前实现）：每轮模型输出 `{ "action": "call_skill|finish", ... }`，执行后追加 Observation，直到 `finish` 或步数上限。
2. **LiteLLM 原生 function calling**（可选升级）：将每个 Skill 暴露为 tool definition，由模型产生 tool_calls；需验证当前 LLM 配置是否支持多轮工具调用。

### SSE 事件扩展

| 阶段 | 当前 `type` | 可选扩展 |
|------|------------|---------|
| 每步开始 | `thinking` | 保持现状 |
| 每步结束 | `thinking` | 可引入 `tool_result` 类型供前端展示工具轨迹 |
| 最终呈现 | `text` / `chart` / `kpi_cards` / `error` | 不变 |

若引入 `tool_result`，需同步 [`frontend/src/types/message.ts`](../../frontend/src/types/message.ts)。

### 核心代码入口

- 编排扩展点：[`backend/agent/runner.py`](../../backend/agent/runner.py)
- ReAct 循环：[`backend/agent/react_runner.py`](../../backend/agent/react_runner.py)
- 单次规划：[`backend/agent/planner.py`](../../backend/agent/planner.py)
