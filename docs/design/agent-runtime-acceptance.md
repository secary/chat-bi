# Agent 运行时验收说明（当前：单次 LLM + 单次 Skill）

本文档描述 **当前已实现** 的 ChatBI Agent 行为，便于产品与 QA 对照 [`runner.py`](../../backend/agent/runner.py)、[`planner.py`](../../backend/agent/planner.py) 做验收，并与经典 ReAct 区分。

## 模式定性

- **不是**「Thought → Action → Observation」多轮闭环（经典 ReAct）。
- **是**「单次 JSON 规划 → 至多一次 Skill 脚本执行 → SSE 输出」的 **Plan-and-Execute**。

## 验收清单

### 1. 单次大模型调用（规划）

- [ ] 每个用户消息对应的后端处理路径中，[`call_llm_for_plan`](../../backend/agent/planner.py) **仅被 await 一次**（成功路径）。
- [ ] 该调用使用 `response_format=json_object`，产出包含 `skill`、`skill_args`、`text`、`chart_plan`、`kpi_cards`、`steps` 等字段的 JSON 计划（字段定义见 [`AGENT_SYSTEM_INSTRUCTION`](../../backend/agent/prompt_builder.py)）。

### 2. 单次 Skill 执行（执行）

- [ ] 当计划中的 `skill` 非空且能在 [`scan_skills`](../../backend/agent/prompt_builder.py) 结果中解析时，[`run_script`](../../backend/agent/executor.py) **最多调用一次**。
- [ ] 当 `skill` 为 null 或无法解析时，不执行脚本，可返回 `text`（若有）并以 `done` 结束。

### 3. Observation 不回灌模型

- [ ] Skill 的 JSON 结果 **不** 作为新一轮 user/assistant 消息再次送入 LLM；直接进入 [`stream_result_events`](../../backend/agent/formatter.py) 生成 SSE。

### 4. System Prompt 与 Skill 列表

- [ ] 每次请求开始时扫描 `skills/*/SKILL.md`，[`build_system_prompt`](../../backend/agent/prompt_builder.py) 中包含当前可用 Skill 及从文档抽取的章节。

### 5. 思考步骤字段（`steps`）

- [ ] Prompt 要求模型输出 `steps` 数组时，**后端当前实现可选择是否将其映射到 SSE**；若以固定文案 `thinking` 为主，需在演示材料中说明与模型 `steps` 的差异。

### 6. 自动化契约

- [ ] [`tests/test_agent_runner_contract.py`](../../tests/test_agent_runner_contract.py) 通过：mock 下每个请求 **1 次** `call_llm_for_plan`、**1 次** `run_script`（当计划含有效 skill 时）。

## 相关文档

- [Agent ReAct 演进设计](./agent-react-evolution.md)（规划中的多步能力与 Observation 格式）。
