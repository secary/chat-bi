from __future__ import annotations

import json
import tempfile
from typing import Any, AsyncGenerator, Dict, List, Optional

from backend.agent.context_window import build_react_context
from backend.agent.executor import (
    find_skill,
    latest_user_upload_path,
    run_script,
    skill_result_log_payload,
    skill_args_for_execution,
)
from backend.agent.formatter import stream_result_events
from backend.agent.intent_guard import small_talk_reply, should_skip_skill_for_message
from backend.agent.observation import summarize_observation
from backend.agent.abort_async import ChatAbortedError
from backend.agent.planner import call_llm_for_react_step
from backend.agent.prompt_builder import (
    SkillDoc,
    build_react_system_prompt,
    scan_skills_enabled,
)
from backend.agent.prompt_subagent import build_react_system_prompt_for_subagent
from backend.agent.query_decision import is_query_plus_decision_text
from backend.agent.react_followup import run_decision_followup
from backend.agent.skill_call_validator import (
    dialogue_text_from_messages,
    validate_skill_call,
    validation_observation_payload,
)
from backend.agent.upload_context import get_cached_file_data
from backend.config import settings
from backend.trace import log_event

OBS_HEADER = "以下为工具执行后的 Observation（JSON 摘要），请基于事实继续推理：\n"
_VISUAL_FIRST_SKILLS = {
    "chatbi-chart-recommendation",
    "chatbi-dashboard-orchestration",
}


def _merge_finish_result(
    plan: Dict[str, Any],
    last_result: Optional[Dict[str, Any]],
    last_skill_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Merges the final LLM finish text with the last skill result.
    Suppresses finish text when the skill already produced visual content (charts/kpis),
    or when the last skill is a decision-advisor that already provided text.
    """
    merged: Dict[str, Any] = dict(last_result or {})
    if _should_suppress_finish_text(last_skill_name, merged):
        merged["text"] = ""
        return merged
    if last_skill_name == "chatbi-decision-advisor" and merged.get("text"):
        return merged
    # skill 已生成图表时，保留 skill 自带文本，不被 LLM finish 文本覆盖
    if merged.get("chart_plan") or merged.get("charts"):
        return merged
    if plan.get("text"):
        merged["text"] = plan["text"]
    return merged


def _should_suppress_finish_text(
    last_skill_name: Optional[str], result: Optional[Dict[str, Any]]
) -> bool:
    """
    Returns True when the last skill is a visual-first skill
    (chatbi-chart-recommendation, chatbi-dashboard-orchestration) and already
    produced charts or KPIs, so the LLM finish
    text should not overwrite the visual content.
    """
    if last_skill_name not in _VISUAL_FIRST_SKILLS:
        return False
    if not isinstance(result, dict):
        return False
    has_charts = bool(result.get("charts"))
    has_kpis = bool(result.get("kpis"))
    return has_charts or has_kpis


def _sink_write(
    sink: Optional[Dict[str, Any]],
    last_result: Optional[Dict[str, Any]],
    last_skill_name: Optional[str],
) -> None:
    """Writes the last executed result and skill name into the result sink dict."""
    if sink is None:
        return
    sink["last_result"] = last_result
    sink["last_skill_name"] = last_skill_name


def _rows_for_followup_chart(result: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not isinstance(result, dict):
        return []
    data = result.get("data")
    if not isinstance(data, dict):
        return []
    rows = data.get("rows")
    if isinstance(rows, list) and rows:
        return rows
    preview_rows = data.get("preview_rows")
    if isinstance(preview_rows, list) and preview_rows:
        return preview_rows
    return []


def _is_file_ingestion_result(result: Optional[Dict[str, Any]]) -> bool:
    return isinstance(result, dict) and str(result.get("kind") or "") == "file_ingestion"


def _file_ingestion_result_path(result: Optional[Dict[str, Any]]) -> str:
    if not isinstance(result, dict):
        return ""
    data = result.get("data")
    if not isinstance(data, dict):
        return ""
    return str(data.get("file") or "")


def _should_short_circuit_repeated_file_ingestion(
    skill_name: str,
    args: List[str],
    last_skill_name: Optional[str],
    last_result: Optional[Dict[str, Any]],
    messages: Optional[List[Dict[str, str]]] = None,
) -> bool:
    if skill_name != "chatbi-file-ingestion" or last_skill_name != "chatbi-file-ingestion":
        return False
    if not _is_file_ingestion_result(last_result):
        return False
    current_path = str(args[0]) if args else ""
    previous_path = _file_ingestion_result_path(last_result)
    if bool(current_path) and current_path == previous_path:
        return True
    if messages:
        upload_path = latest_user_upload_path(messages)
        if upload_path and get_cached_file_data(upload_path):
            return True
    return False


def _chart_recommendation_args(
    user_text: str,
    plan_args: List[str],
    last_result: Optional[Dict[str, Any]],
) -> List[str]:
    rows = _rows_for_followup_chart(last_result)
    if not rows:
        return plan_args or [user_text]
    payload = {"question": user_text, "rows": rows}
    return [json.dumps(payload, ensure_ascii=False)]


def _auto_analysis_args(
    user_text: str,
    plan_args: List[str],
    last_result: Optional[Dict[str, Any]],
    cached_rows: Optional[List[Dict[str, Any]]] = None,
    column_labels: Optional[Dict[str, Any]] = None,
) -> List[str]:
    rows = _rows_for_followup_chart(last_result) or (cached_rows or [])
    if not rows:
        return plan_args or [user_text]
    payload: Dict[str, Any] = {"question": user_text, "rows": rows}
    if column_labels:
        payload["column_labels"] = column_labels
    if _is_confirmation_request(user_text):
        payload["mode"] = "execute"
    return ["--input-file", _write_auto_analysis_payload(payload)]


def _is_terminal_auto_analysis_result(skill_name: str, result: Optional[Dict[str, Any]]) -> bool:
    if skill_name != "chatbi-auto-analysis" or not isinstance(result, dict):
        return False
    data = result.get("data")
    if not isinstance(data, dict):
        return False
    if isinstance(data.get("analysis_proposal"), dict):
        return True
    if isinstance(data.get("dashboard_middleware"), dict):
        return True
    return str(data.get("status") or "") in {"need_confirmation", "ready"}


def _write_auto_analysis_payload(payload: Dict[str, Any]) -> str:
    handle = tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        prefix="chatbi-auto-analysis-",
        suffix=".json",
        delete=False,
    )
    with handle:
        json.dump(payload, handle, ensure_ascii=False)
    return handle.name


def _has_upload_context(messages: List[Dict[str, str]]) -> bool:
    return bool(latest_user_upload_path(messages))


def _is_visual_request(text: str) -> bool:
    markers = ("画图", "图表", "可视化", "展示")
    return bool(text) and any(marker in text for marker in markers)


def _is_auto_analysis_request(text: str) -> bool:
    markers = (
        "分析",
        "指标",
        "看板",
        "仪表盘",
        "dashboard",
        "采纳",
        "确认",
        "roi",
        "ROI",
        "留存",
        "不良",
        "逾期",
        "趋势",
    )
    return bool(text) and any(marker in text for marker in markers)


def _is_confirmation_request(text: str) -> bool:
    return bool(text) and any(word in text for word in ["采纳", "确认", "开始", "生成看板"])


def _enforce_upload_skill(
    skill_name: str,
    user_text: str,
    messages: List[Dict[str, str]],
    last_result: Optional[Dict[str, Any]],
) -> str:
    if not _has_upload_context(messages):
        return skill_name
    if skill_name == "chatbi-file-ingestion":
        return skill_name
    if _rows_for_followup_chart(last_result) and _is_auto_analysis_request(user_text):
        return "chatbi-auto-analysis"
    if skill_name != "chatbi-semantic-query":
        return skill_name
    if _rows_for_followup_chart(last_result) and _is_visual_request(user_text):
        return "chatbi-chart-recommendation"
    return "chatbi-file-ingestion"


def _skill_log_payload(
    skill_name: str,
    skill_doc: SkillDoc,
    *,
    agent_id: Optional[str],
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "skill": skill_name,
        "agent_id": agent_id or "single",
        "validator_requires": list(skill_doc.validator_requires or []),
    }
    if extra:
        payload.update(extra)
    return payload


async def stream_chat_react(
    messages: List[Dict[str, str]],
    trace_id: str = "",
    skill_db_overrides: Optional[Dict[str, str]] = None,
    memory_block: Optional[str] = None,
    skill_docs: Optional[List[SkillDoc]] = None,
    role_prompt: Optional[str] = None,
    result_sink: Optional[Dict[str, Any]] = None,
    subagent_react: bool = False,
    specialist_agent_id: Optional[str] = None,
    session_id: Optional[int] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    ReAct multi-step agent loop.
    Each iteration: LLM decides next action {"thought", "action", "skill", "skill_args"} → executes a skill → summarizes observation → repeats.
    Stops when the LLM outputs 'finish/done/answer', or when agent_max_steps is exhausted.
    action == "call_skill", execute Skill，append observation result to working list.
    Auto-runs chatbi-decision-advisor as a followup when query+decision intent is detected.
    """
    log_event(
        trace_id,
        "agent.runner",
        "started",
        payload={
            "message_count": len(messages),
            "mode": "react_subagent" if subagent_react else "react",
        },
    )
    skills = skill_docs if skill_docs is not None else scan_skills_enabled(settings.skills_dir)
    allowed_slugs = {d.skill_dir.name for d in skills}
    user_text = next(
        (str(m.get("content", "")) for m in reversed(messages) if m.get("role") == "user"),
        "",
    )
    if should_skip_skill_for_message(user_text):
        log_event(trace_id, "agent.runner", "skip_skill_small_talk", payload={"mode": "react"})
        _sink_write(result_sink, None, None)
        yield {"type": "thinking", "content": "识别为简单话语，直接回复。"}
        yield {"type": "text", "content": small_talk_reply(user_text)}
        yield {"type": "done", "content": None}
        return

    """
    Build the system prompt for the ReAct agent.
    It includes the skills, the role prompt, and the memory block.
    The role prompt is the user's role in the conversation.
    The memory block is the memory of the agent.
    The skills are the skills that the agent can use.
    The system prompt is the prompt that the agent uses to make a decision.
    """
    system_prompt = (
        build_react_system_prompt_for_subagent(skills)
        if subagent_react
        else build_react_system_prompt(skills)
    )
    if role_prompt and role_prompt.strip():
        system_prompt = role_prompt.strip() + "\n\n" + system_prompt
    if memory_block and memory_block.strip():
        system_prompt = memory_block.strip() + "\n\n" + system_prompt

    # Inject sliding window context for long conversation management
    if session_id:
        conversation_context = build_react_context(session_id, user_text, messages)
        if conversation_context.strip():
            system_prompt = system_prompt + "\n\n" + conversation_context

    """
    working: 一个消息列表，用于存储对话历史和obs(observation的内容)
    """
    working = [dict(m) for m in messages]
    last_skill_name: Optional[str] = None
    last_result: Optional[Dict[str, Any]] = None
    called_skills: list[str] = []
    last_ingestion_rows: List[Dict[str, Any]] = []
    last_ingestion_column_labels: Optional[Dict[str, Any]] = None

    yield {"type": "thinking", "content": "正在分析您的问题（ReAct 多步推理）..."}

    """
    ReAct loop:
    LLM decides next action {"thought", "action", "skill", "skill_args"} → executes a skill → summarizes observation → repeats.
    The agent_max_steps is 8 by default. If the agent_max_steps is reached, the agent will return the last result.
    """
    from backend.agent.abort_state import is_aborted as _is_aborted

    for step in range(settings.agent_max_steps):
        if _is_aborted(trace_id):
            log_event(trace_id, "agent.runner", "aborted", level="INFO")
            yield {"type": "thinking", "content": "用户中止了查询。"}
            _sink_write(result_sink, last_result, last_skill_name)
            yield {"type": "done", "content": None}
            return

        log_event(
            trace_id,
            "agent.planner",
            "react.step",
            payload={"step": step + 1, "max_steps": settings.agent_max_steps},
        )
        try:
            """
            Call LLM for the next ReAct step.
            将system prompt + 对话的上下文 + skill所执行的结果obs，一起传给LLM，得到下一步的决策。
            LLM 返回 {"thought", "action", "skill", "skill_args"}
            """
            plan = await call_llm_for_react_step(system_prompt, working, trace_id=trace_id)
        except ChatAbortedError:
            log_event(trace_id, "agent.runner", "aborted", level="INFO")
            yield {"type": "thinking", "content": "用户中止了查询。"}
            _sink_write(result_sink, last_result, last_skill_name)
            yield {"type": "done", "content": None}
            return
        except Exception as exc:
            if last_result:
                yield {
                    "type": "thinking",
                    "content": f"模型收尾失败，展示最后一次工具结果：{exc}",
                }
                async for event in stream_result_events(
                    last_skill_name or "skill", {}, last_result
                ):
                    yield event
                _sink_write(result_sink, last_result, last_skill_name)
                yield {"type": "done", "content": None}
                return
            raise
        if not plan:
            if last_result:
                yield {"type": "thinking", "content": "模型未返回有效 JSON，展示最后一次工具结果。"}
                async for event in stream_result_events(
                    last_skill_name or "skill", {}, last_result
                ):
                    yield event
                _sink_write(result_sink, last_result, last_skill_name)
                yield {"type": "done", "content": None}
                return
            _sink_write(result_sink, None, None)
            yield {"type": "error", "content": "模型未返回有效 JSON。"}
            yield {"type": "done", "content": None}
            return

        thought = plan.get("thought")
        if isinstance(thought, str) and thought.strip():
            yield {"type": "thinking", "content": thought.strip()}

        action = str(plan.get("action") or "finish").strip().lower()
        if action in ("finish", "done", "answer"):
            yield {"type": "thinking", "content": "正在整理回答..."}
            merged = _merge_finish_result(plan, last_result, last_skill_name)
            skill_label = last_skill_name or "chatbi-semantic-query"
            async for event in stream_result_events(skill_label, plan, merged):
                yield event
            log_event(
                trace_id,
                "agent.runner",
                "completed",
                payload={"mode": "react", "steps": step + 1},
            )
            _sink_write(result_sink, last_result, last_skill_name)
            yield {"type": "done", "content": None}
            return

        if action == "ask":
            ask_text = plan.get("text", "请问还有什么需要帮助的？")
            yield {"type": "thinking", "content": "正在询问补充信息..."}
            yield {"type": "text", "content": ask_text}
            log_event(
                trace_id,
                "agent.runner",
                "completed",
                payload={"mode": "react", "action": "ask", "steps": step + 1},
            )
            _sink_write(result_sink, last_result, last_skill_name)
            yield {"type": "done", "content": None}
            return

        if action != "call_skill":
            _sink_write(result_sink, last_result, last_skill_name)
            yield {
                "type": "error",
                "content": f"无法识别的 action：{plan.get('action')}",
            }
            yield {"type": "done", "content": None}
            return

        """
        Execute the skill by given the skill name.
        """
        skill_name = plan.get("skill")
        if not skill_name or not isinstance(skill_name, str):
            _sink_write(result_sink, last_result, last_skill_name)
            yield {"type": "error", "content": "call_skill 缺少有效的 skill 名称。"}
            yield {"type": "done", "content": None}
            return
        skill_name = _enforce_upload_skill(skill_name, user_text, messages, last_result)
        # When auto-analysis is called without any row data but a file was uploaded,
        # redirect to file-ingestion first so rows are available on the next step.
        if (
            skill_name == "chatbi-auto-analysis"
            and _has_upload_context(messages)
            and not _rows_for_followup_chart(last_result)
            and not last_ingestion_rows
        ):
            skill_name = "chatbi-file-ingestion"

        skill_doc = find_skill(skills, skill_name)
        if not skill_doc:
            available = ", ".join(sorted(allowed_slugs)) if allowed_slugs else "（无）"
            _sink_write(result_sink, last_result, last_skill_name)
            yield {
                "type": "error",
                "content": f"未找到技能：{skill_name}。本专线可用技能：{available}",
            }
            yield {"type": "done", "content": None}
            return

        validation = validate_skill_call(
            skill_doc,
            allowed_slugs=allowed_slugs,
            dialogue_text=dialogue_text_from_messages(working),
            last_result=last_result,
            user_text=user_text,
        )
        if not validation.ok:
            raw_args = plan.get("skill_args") or []
            assistant_note = json.dumps(
                {"action": "call_skill", "skill": skill_name, "skill_args": raw_args},
                ensure_ascii=False,
            )
            obs = validation_observation_payload(skill_name, validation, allowed_slugs)
            log_event(
                trace_id,
                "agent.skill",
                "validation_rejected",
                validation.reason[:500],
                payload={
                    "proposed_skill": skill_name,
                    "reason": validation.reason,
                    "rule": validation.rule,
                    "user_snippet": (user_text or "")[:200],
                    "agent_id": specialist_agent_id or "single",
                },
                level="WARNING",
            )
            working.append({"role": "assistant", "content": assistant_note})
            working.append({"role": "user", "content": OBS_HEADER + obs})
            yield {
                "type": "thinking",
                "content": f"技能校验未通过：{validation.reason}",
            }
            continue

        yield {"type": "thinking", "content": f"正在执行 Skill「{skill_name}」..."}

        """
        transfer llm raw args into real args for the skill.
        for example:
            LLM plan: {"skill": "chatbi-file-ingestion", "skill_args": ["帮我分析"]}
            skill_args_for_execution("chatbi-file-ingestion", ["帮我分析"], messages)
            find the real address of a file by the user's upload path, mathch /tmp/chatbi-uploads/xxx.csv
            return ["/tmp/chatbi-uploads/xxx.csv", "--sheet", "Sheet1"]
            assistant_note: {"action": "call_skill", "skill": "chatbi-file-ingestion", "skill_args": ["/tmp/chatbi-uploads/xxx.csv", "--sheet", "Sheet1"]}
        """
        raw_args = plan.get("skill_args") or []
        args = skill_args_for_execution(skill_name, raw_args, messages)
        if skill_name == "chatbi-auto-analysis":
            args = _auto_analysis_args(
                user_text,
                args,
                last_result,
                cached_rows=last_ingestion_rows or None,
                column_labels=last_ingestion_column_labels,
            )
        if skill_name == "chatbi-chart-recommendation":
            args = _chart_recommendation_args(user_text, args, last_result)
        if _should_short_circuit_repeated_file_ingestion(
            skill_name,
            args,
            last_skill_name,
            last_result,
            messages,
        ):
            yield {
                "type": "thinking",
                "content": "文件已解析完成，正在整理结果...",
            }
            merged = _merge_finish_result(plan, last_result, last_skill_name)
            async for event in stream_result_events(last_skill_name or skill_name, plan, merged):
                yield event
            log_event(
                trace_id,
                "agent.runner",
                "completed",
                payload={"mode": "react", "short_circuit": "repeated_file_ingestion"},
            )
            _sink_write(result_sink, last_result, last_skill_name)
            yield {"type": "done", "content": None}
            return
        assistant_note = json.dumps(
            {"action": "call_skill", "skill": skill_name, "skill_args": args},
            ensure_ascii=False,
        )
        try:
            log_event(
                trace_id,
                "agent.skill",
                "started",
                payload=_skill_log_payload(
                    skill_name,
                    skill_doc,
                    agent_id=specialist_agent_id,
                    extra={"args": args},
                ),
            )
            result = run_script(
                skill_doc,
                args,
                trace_id=trace_id,
                skill_db_overrides=skill_db_overrides,
            )
            log_event(
                trace_id,
                "agent.skill",
                "completed",
                payload=_skill_log_payload(
                    skill_name,
                    skill_doc,
                    agent_id=specialist_agent_id,
                    extra=skill_result_log_payload(result),
                ),
            )
            last_skill_name = skill_name
            last_result = result
            called_skills.append(skill_name)
            if skill_name == "chatbi-file-ingestion":
                ingested = _rows_for_followup_chart(result)
                if ingested:
                    last_ingestion_rows = ingested
                cl = (result.get("data") or {}).get("column_labels")
                if isinstance(cl, dict):
                    last_ingestion_column_labels = cl
            if _is_terminal_auto_analysis_result(skill_name, result):
                yield {
                    "type": "thinking",
                    "content": "自动分析已生成结构化结果，正在展示...",
                }
                async for event in stream_result_events(skill_name, plan, result):
                    yield event
                log_event(
                    trace_id,
                    "agent.runner",
                    "completed",
                    payload={"mode": "react", "short_circuit": "auto_analysis"},
                )
                _sink_write(result_sink, last_result, last_skill_name)
                yield {"type": "done", "content": None}
                return
            obs = summarize_observation(skill_name, result)
        except Exception as exc:
            log_event(
                trace_id,
                "agent.skill",
                "failed",
                str(exc),
                {"skill": skill_name},
                "ERROR",
            )
            obs = json.dumps(
                {"skill": skill_name, "ok": False, "error": str(exc)},
                ensure_ascii=False,
            )

        working.append({"role": "assistant", "content": assistant_note})
        working.append({"role": "user", "content": OBS_HEADER + obs})
        yield {"type": "thinking", "content": "已收到 Observation，继续推理..."}

        if (
            skill_name == "chatbi-semantic-query"
            and is_query_plus_decision_text(user_text)
            and "chatbi-decision-advisor" not in called_skills
        ):
            advice_doc = find_skill(skills, "chatbi-decision-advisor")
            if advice_doc:
                try:
                    followup_events, advice_result, followup_messages = run_decision_followup(
                        advice_doc,
                        messages,
                        user_text,
                        trace_id,
                        skill_db_overrides,
                    )
                    for event in followup_events:
                        yield event
                    last_skill_name = "chatbi-decision-advisor"
                    last_result = advice_result
                    called_skills.append("chatbi-decision-advisor")
                    working.extend(followup_messages)
                except Exception as exc:
                    yield {"type": "error", "content": f"决策建议执行失败：{exc}"}
                    yield {"type": "done", "content": None}
                    return

    if last_result:
        yield {
            "type": "thinking",
            "content": "已达到最大推理步数，展示最后一次工具结果。",
        }
        fallback_plan: Dict[str, Any] = {
            "chart_plan": None,
            "kpi_cards": None,
            "text": "已达到最大推理步数，以上为最后一次工具返回的数据摘要。",
        }

        """
        Merge llm last output and last skill output.

        For example:
            call_skill → chatbi-semantic-query → skill result = {"text": "本月销售额 100 万", "chart_plan": {...}}
            LLM result= action="finish", plan={"text": "以下是您要求的数据..."}

            final result: skill result(chart/kpis/text) + llm result(text)
        """
        merged = _merge_finish_result(fallback_plan, last_result, last_skill_name)
        """
        stream_result_events:
        transfer the skill result to the frontend page by sse.
        """
        async for event in stream_result_events(last_skill_name or "skill", fallback_plan, merged):
            yield event
    else:
        yield {
            "type": "text",
            "content": "已达到最大推理步数，尚未获得工具结果。请简化问题或稍后重试。",
        }
    log_event(
        trace_id,
        "agent.runner",
        "completed",
        payload={"mode": "react", "exhausted": True},
    )
    _sink_write(result_sink, last_result, last_skill_name)
    yield {"type": "done", "content": None}
