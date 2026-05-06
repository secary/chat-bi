# Agent 运行时验收说明（ReAct 默认 + Legacy 可选）

本文档描述 ChatBI Agent 的两种运行时，便于产品与 QA 对照 [`runner.py`](../../backend/agent/runner.py)、[`planner.py`](../../backend/agent/planner.py)、[`react_runner.py`](../../backend/agent/react_runner.py) 做验收。

环境变量（参见根目录 [`.env.example`](../../.env.example)）：

- **`CHATBI_AGENT_REACT`**：默认为开启（`1` / 非 `0` / 非 `false`）。关闭时使用 Legacy 单次规划路径。
- **`CHATBI_AGENT_MAX_STEPS`**：ReAct 模式下每则用户消息允许的 **LLM 调用次数**上限（默认 `8`）。一次典型的「先调用 Skill、再总结收尾」至少需要 **2** 轮 LLM。

---

## A. ReAct 模式（默认）

### 模式定性

- **是**「Thought（JSON）→ Action（Skill）→ Observation（摘要回灌）→ … → finish」的多轮闭环。
- 实现位置：[ `stream_chat_react`](../../backend/agent/react_runner.py)；每轮调用 [`call_llm_for_react_step`](../../backend/agent/planner.py)。

### 验收清单

- [ ] 每轮模型输出 JSON，包含 `action`：`call_skill` 或 `finish`（见 [`build_react_system_prompt`](../../backend/agent/prompt_builder.py)）。
- [ ] `call_skill` 时执行至多 **一次** [`run_script`](../../backend/agent/executor.py)，随后将 [`summarize_observation`](../../backend/agent/observation.py) 追加为 user 消息并继续下一轮 LLM。
- [ ] `finish` 时合并最后一次工具结果与 `text` / `chart_plan`，经 [`stream_result_events`](../../backend/agent/formatter.py) 输出 SSE。
- [ ] 达到 `CHATBI_AGENT_MAX_STEPS` 仍未 `finish` 时，有明确的兜底文案或最后一次工具结果展示。
- [ ] [`tests/test_react_runner.py`](../../tests/test_react_runner.py) 通过。

---

## B. Legacy 模式（`CHATBI_AGENT_REACT=0`）

### 模式定性

- **不是**经典 ReAct；**是**「单次 JSON 规划 → 至多一次 Skill → SSE」的 **Plan-and-Execute**。

### 验收清单

### 1. 单次大模型调用（规划）

- [ ] 每个用户消息对应的后端处理路径中，[`call_llm_for_plan`](../../backend/agent/planner.py) **仅被 await 一次**（成功路径）。
- [ ] 该调用使用 `response_format=json_object`，产出包含 `skill`、`skill_args`、`text`、`chart_plan`、`kpi_cards`、`steps` 等字段的 JSON 计划（字段定义见 [`AGENT_SYSTEM_INSTRUCTION`](../../backend/agent/prompt_builder.py)）。

### 2. 单次 Skill 执行（执行）

- [ ] 当计划中的 `skill` 非空且能在 [`scan_skills`](../../backend/agent/prompt_builder.py) 结果中解析时，[`run_script`](../../backend/agent/executor.py) **最多调用一次**。
- [ ] 当 `skill` 为 null 或无法解析时，不执行脚本，可返回 `text`（若有）并以 `done` 结束。

### 3. Observation 不回灌模型

- [ ] Skill 结果 **不** 再次送入 LLM；直接进入 [`stream_result_events`](../../backend/agent/formatter.py) 生成 SSE。

### 4. System Prompt 与 Skill 列表

- [ ] 每次请求开始时扫描 `skills/*/SKILL.md`，[`build_system_prompt`](../../backend/agent/prompt_builder.py) 中包含当前可用 Skill 及从文档抽取的章节。

### 5. 自动化契约

- [ ] [`tests/test_agent_runner_contract.py`](../../tests/test_agent_runner_contract.py) 通过：在 **Legacy** 配置下 mock，每个请求 **1 次** `call_llm_for_plan`、**1 次** `run_script`（当计划含有效 skill 时）。

## 相关文档

- [Agent ReAct 演进设计](./agent-react-evolution.md)（补充设计与后续扩展点）。
