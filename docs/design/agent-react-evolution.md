# Agent ReAct 演进设计（后续迭代）

本文档约定 **若** 产品需要将 ChatBI Agent 从「单次规划 + 单次 Skill」升级为经典 **ReAct**（想 → 做 → 观察 → 再想…）时可落地的设计要点，便于与 [`SkillResult`](../../backend/agent/protocol.py)、SSE 衔接。

## 目标行为

- 同一用户消息的处理周期内，允许 **多次** Skill 调用（例如先别名校验再问数，或多次语义查询不同指标）。
- 每一步工具返回的 **Observation** 进入下一轮 LLM 上下文，模型可基于真实输出再决策。

## 控制参数

| 参数 | 建议 | 说明 |
|------|------|------|
| `max_steps` | 默认 5～8，可配置 | 防止无限循环与费用失控；达到上限时强制要求模型输出最终 `text` 或标记失败原因。 |
| `step_timeout` | 与现有脚本超时一致或略大 | 单步 Skill 仍沿用 `executor` 的 `subprocess` 超时策略。 |

环境变量命名示例（实现时落地）：`CHATBI_AGENT_MAX_STEPS`。

## 消息与 Observation 格式

### 追加到 LLM 的对话结构（建议）

在现有 `messages`（user/history）基础上，每完成一步 Skill 后追加两条逻辑消息（具体 role 以实现选型为准）：

1. **Assistant（工具调用摘要）**  
   - `skill`: 技能名  
   - `args`: 传入脚本的参数列表  
   - `thought`: 可选，模型本轮简短推理（若使用原生 tool_calls 则省略手写 JSON）

2. **User 或 Tool（Observation）**  
   - `observation`: 结构化对象，见下文。

### Observation 载荷（建议 Schema）

对脚本输出做 **摘要后** 再回灌，避免把大屏表数据撑爆上下文：

```json
{
  "skill": "chatbi-semantic-query",
  "ok": true,
  "kind": "table",
  "row_count": 12,
  "columns": ["区域", "销售额"],
  "sample_rows": [{"区域": "华东", "销售额": "100"}],
  "error": null,
  "trace_id": "..."
}
```

- 失败时：`ok: false`，`error` 为脚本 stderr 或归一化错误信息。
- 决策类 Skill 可额外包含 `kpis_preview`、`text_excerpt`（截断 Markdown）。

归一化入口仍使用 [`normalize_skill_result`](../../backend/agent/executor.py) / [`protocol.py`](../../backend/agent/protocol.py)，再在 runner 内增加 **摘要函数** `summarize_for_observation(result: dict) -> dict`。

## 与 SSE 的衔接

| 事件阶段 | 建议 `type` | 内容 |
|----------|----------------|------|
| 每步开始 | `thinking` | 可选：`正在执行第 n 步：{skill}` |
| 每步结束 | `thinking` 或自定义 `tool_result` | Observation 摘要（若产品需要前端展示工具轨迹）；**勿**默认流式输出完整大表 JSON。 |
| 最终呈现 | `text` / `chart` / `kpi_cards` / `error` | 与现有一致；最后一步可由模型指定 chart_plan，或沿用最后一轮 Skill 结果走 [`formatter.py`](../../backend/agent/formatter.py)。 |

若引入 `tool_result` 新类型，需同步 [`frontend/src/types/message.ts`](../../frontend/src/types/message.ts) 与 `useChat` 聚合逻辑。

## Planner 实现路径（二选一或组合）

1. **保留 JSON 计划，外层循环**  
   每轮模型输出 `{ "action": "call_skill|finish", "skill", "skill_args", ... }`，执行后追加 Observation，直到 `finish` 或 `max_steps`。

2. **LiteLLM 原生 `tools` / function calling**  
   将每个 Skill 暴露为一个 tool definition；由模型产生 tool_calls，宿主执行脚本并把结果以 `tool` role 传回。需验证当前 `LLM_MODEL` 与 LiteLLM 配置是否支持多轮工具调用。

## 与「脚本内多图」的边界

- **脚本内** 返回 `charts[]` 仍适用于单次 Skill 多图场景（见 [`formatter.py`](../../backend/agent/formatter.py)）。
- **Agent 级 ReAct** 用于 **跨 Skill** 或 **依赖上一步真实输出再决策** 的场景；二者可同时存在。

## 参考代码入口

- 编排扩展点：[`backend/agent/runner.py`](../../backend/agent/runner.py)
- 单次规划：[`backend/agent/planner.py`](../../backend/agent/planner.py)
