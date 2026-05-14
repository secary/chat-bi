"""Manager LLM: single JSON plan with subtasks → specialists (topological order)."""

from __future__ import annotations

import json
from collections import deque
from typing import Any, Dict, List, Optional, Tuple

from backend.agent.multi_agent_registry import (
    agent_label,
    list_registry_agent_ids,
    max_agents_per_round,
    skills_for_agent,
)
from backend.agent.planner import parse_json_object
from backend.llm_runtime import chatbi_acompletion
from backend.trace import log_event


def _dialogue_tail_for_manager(messages: List[Dict[str, str]], max_msgs: int = 12) -> str:
    tail = messages[-max_msgs:] if len(messages) > max_msgs else messages
    lines: List[str] = []
    for m in tail:
        role = str(m.get("role") or "")
        content = str(m.get("content") or "").strip()
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines) if lines else ""


def _registry_capability_block() -> str:
    lines_out: List[str] = []
    for aid in list_registry_agent_ids():
        docs = skills_for_agent(aid)
        if not docs:
            continue
        lab = agent_label(aid)
        names = ", ".join(d.skill_dir.name for d in docs)
        lines_out.append(f"- `{aid}`（{lab}）可用技能：{names}")
    return (
        "\n".join(lines_out) if lines_out else "（当前无可用专线：请检查 registry 与技能启用状态）"
    )


def _manager_system_prompt() -> str:
    cap = max_agents_per_round()
    caps = _registry_capability_block()
    return f"""你是 ChatBI 多专线的 **Manager**：根据用户对话，将需求拆解为 1～{cap} 个子任务，并指派给下方专线之一执行。
你只能指派 registry 中列出的专线 id；每个子任务必须对应一条仍有「可用技能」的专线。

## 专线与能力（仅能使用表中技能，勿指派无技能专线）
{caps}

## 输出 JSON（仅此一个对象）
{{
  "user_intent_summary": "一句话概括用户意图",
  "decomposition_reason": "为何这样拆解或为何不拆解（单任务时说明）",
  "tasks": [
    {{
      "agent_id": "专线id",
      "handoff_instruction": "交给该专线的具体中文指令（可引用用户原话中的指标/时间范围）",
      "depends_on": null
    }}
  ]
}}

规则：
- `tasks` 至少 1 条、至多 {cap} 条；`agent_id` 必须出现在上表专线 id 中。
- `depends_on`：若该子任务依赖另一子任务的输出，填被依赖任务在 `tasks` 数组中的 **0-based 下标**；无依赖填 null。禁止自依赖；禁止环。
- 简单问题可只输出 1 条 task；复杂问题可拆成多条并按依赖链排列（先查询后解读等）。
- 不要输出 Markdown 围栏。"""


def _is_valid_dep_index(d: Any, n: int, self_idx: int) -> bool:
    if d is None:
        return True
    if type(d) is not int:
        return False
    return 0 <= int(d) < n and int(d) != self_idx


def topological_order(deps: List[Optional[int]]) -> Optional[List[int]]:
    """deps[i] = prerequisite index or None. Returns execution order of indices or None if cycle."""
    n = len(deps)
    indeg = [0] * n
    adj: List[List[int]] = [[] for _ in range(n)]
    for i in range(n):
        p = deps[i]
        if p is not None:
            adj[p].append(i)
            indeg[i] += 1
    q: deque[int] = deque(i for i in range(n) if indeg[i] == 0)
    order: List[int] = []
    while q:
        u = q.popleft()
        order.append(u)
        for v in adj[u]:
            indeg[v] -= 1
            if indeg[v] == 0:
                q.append(v)
    if len(order) != n:
        return None
    return order


def validate_and_order_tasks(
    raw_tasks: List[Any],
    cap: int,
) -> Optional[List[Tuple[int, Dict[str, Any]]]]:
    """
    Validates task list and returns (original_index, task_dict) in execution order, or None.
    """
    if not isinstance(raw_tasks, list) or not raw_tasks:
        return None
    if len(raw_tasks) > cap:
        return None
    reg = set(list_registry_agent_ids())
    normalized: List[Dict[str, Any]] = []
    deps: List[Optional[int]] = []
    for i, item in enumerate(raw_tasks):
        if not isinstance(item, dict):
            return None
        aid = str(item.get("agent_id") or "").strip()
        hi = str(item.get("handoff_instruction") or "").strip()
        if not aid or not hi or aid not in reg:
            return None
        if not skills_for_agent(aid):
            return None
        d_raw = item.get("depends_on")
        if d_raw is None or d_raw is False:
            dep: Optional[int] = None
        elif type(d_raw) is int:
            dep = int(d_raw)
        else:
            return None
        if not _is_valid_dep_index(dep, len(raw_tasks), i):
            return None
        normalized.append({"agent_id": aid, "handoff_instruction": hi, "depends_on": dep})
        deps.append(dep)
    order = topological_order(deps)
    if order is None:
        return None
    return [(idx, normalized[idx]) for idx in order]


async def call_manager_plan_llm(
    messages: List[Dict[str, str]],
    trace_id: str = "",
) -> Optional[Dict[str, Any]]:
    """Returns parsed Manager JSON or None on failure."""
    body = _dialogue_tail_for_manager(messages)
    llm_messages = [
        {"role": "system", "content": _manager_system_prompt()},
        {"role": "user", "content": f"请根据以下对话输出规划 JSON：\n{body}"},
    ]
    try:
        resp = await chatbi_acompletion(
            messages=llm_messages,
            response_format={"type": "json_object"},
            temperature=0.15,
        )
    except Exception as exc:
        log_event(
            trace_id,
            "agent.multi_manager",
            "plan_failed",
            str(exc),
            level="WARN",
        )
        return None
    content = resp.choices[0].message.content
    if not content:
        return None
    try:
        return parse_json_object(content)
    except (json.JSONDecodeError, ValueError):
        log_event(
            trace_id,
            "agent.multi_manager",
            "plan_parse_failed",
            content[:240],
            level="WARN",
        )
        return None
