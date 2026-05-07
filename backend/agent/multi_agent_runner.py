"""Multi-agent orchestration: route → specialists (filtered skills) → summarize."""

from __future__ import annotations

from typing import Any, AsyncGenerator, Dict, List, Optional

from backend.agent.multi_agent_registry import (
    agent_label,
    agent_role_prompt,
    list_registry_agent_ids,
    max_agents_per_round,
    skills_for_agent,
)
from backend.agent.multi_agent_router import call_route_llm
from backend.agent.multi_agent_summarize import call_summarize_llm
from backend.agent.observation import summarize_observation
from backend.agent.formatter import stream_result_events
from backend.agent.runner import stream_specialist
from backend.trace import log_event


def _latest_user_question(messages: List[Dict[str, str]]) -> str:
    for m in reversed(messages):
        if m.get("role") == "user":
            return str(m.get("content") or "")
    return ""


def _pick_route_agents(route: Optional[Dict[str, Any]]) -> List[str]:
    if not route or not isinstance(route, dict):
        return []
    raw = route.get("agents")
    if not isinstance(raw, list):
        return []
    cap = max_agents_per_round()
    out: List[str] = []
    reg = set(list_registry_agent_ids())
    for item in raw:
        aid = str(item).strip()
        if not aid or aid in out or aid not in reg:
            continue
        if not skills_for_agent(aid):
            continue
        out.append(aid)
        if len(out) >= cap:
            break
    return out


async def stream_chat_multi_agent(
    messages: List[Dict[str, str]],
    trace_id: str = "",
    skill_db_overrides: Optional[Dict[str, str]] = None,
    memory_block: Optional[str] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    log_event(
        trace_id,
        "agent.multi",
        "started",
        payload={"message_count": len(messages)},
    )
    route = await call_route_llm(messages, trace_id=trace_id)
    chosen = _pick_route_agents(route)
    if route:
        rs = route.get("routing_reason") or ""
        yield {
            "type": "thinking",
            "content": f"[路由] {rs}".strip() or "[路由] 已完成专线选择。",
        }
        summary = route.get("user_intent_summary")
        if isinstance(summary, str) and summary.strip():
            yield {"type": "thinking", "content": f"[路由] 意图：{summary.strip()}"}

    if not chosen:
        log_event(trace_id, "agent.multi", "fallback_single", level="INFO")
        from backend.agent.runner import stream_chat as _single

        async for event in _single(
            messages,
            trace_id=trace_id,
            skill_db_overrides=skill_db_overrides,
            memory_block=memory_block,
            multi_agents=False,
        ):
            yield event
        return

    blocks: List[Dict[str, str]] = []
    last_result: Optional[Dict[str, Any]] = None
    last_skill_name: Optional[str] = None

    for agent_id in chosen:
        label = agent_label(agent_id)
        role = agent_role_prompt(agent_id)
        docs = skills_for_agent(agent_id)
        if not docs:
            yield {
                "type": "thinking",
                "content": f"[{label}] 无可用技能，跳过。",
            }
            continue
        sink: Dict[str, Any] = {}
        acc_text = ""
        async for event in stream_specialist(
            messages,
            docs,
            role_prompt=role,
            trace_id=trace_id,
            skill_db_overrides=skill_db_overrides,
            memory_block=memory_block,
            result_sink=sink,
        ):
            et = event.get("type")
            if et == "thinking":
                c = str(event.get("content") or "")
                yield {"type": "thinking", "content": f"[{label}] {c}"}
            elif et == "text":
                acc_text += str(event.get("content") or "")
            elif et == "chart":
                pass
            elif et == "kpi_cards":
                pass
            elif et == "error":
                yield {
                    "type": "thinking",
                    "content": f"[{label}] 错误：{event.get('content')}",
                }

        lr = sink.get("last_result")
        lsn = sink.get("last_skill_name")
        if isinstance(lr, dict):
            last_result = lr
        if isinstance(lsn, str) and lsn:
            last_skill_name = lsn
        obs = (
            summarize_observation(str(lsn or "skill"), lr)
            if isinstance(lr, dict)
            else (acc_text[:1200] if acc_text else "（无工具结果）")
        )
        blocks.append(
            {
                "agent": agent_id,
                "label": label,
                "observation": obs,
            }
        )

    q = _latest_user_question(messages)
    yield {"type": "thinking", "content": "[汇总] 正在整合各专线结论..."}
    plan = await call_summarize_llm(q, blocks, trace_id=trace_id)
    if not plan or not isinstance(plan, dict):
        yield {
            "type": "text",
            "content": "汇总阶段未能生成回答，请重试或关闭多专线模式。",
        }
        log_event(trace_id, "agent.multi", "summary_empty", level="WARN")
        yield {"type": "done", "content": None}
        return

    skill_label = last_skill_name or "chatbi-semantic-query"
    merged: Dict[str, Any] = dict(last_result) if last_result else {}
    if plan.get("text"):
        merged["text"] = plan["text"]

    yield {"type": "thinking", "content": "[汇总] 正在输出最终结论..."}
    async for event in stream_result_events(skill_label, plan, merged):
        yield event

    log_event(
        trace_id,
        "agent.multi",
        "completed",
        payload={"agents": chosen},
    )
    yield {"type": "done", "content": None}
