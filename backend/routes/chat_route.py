"""SSE /chat with optional session persistence."""

from __future__ import annotations

import json
import re
from time import perf_counter
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from backend.agent.runner import stream_chat
from backend.auth_deps import get_current_user
from backend.connection_repo import resolve_skill_db_env
from backend.http_utils import request_trace_id
from backend.agent.upload_context import augment_messages_for_upload_followup
from backend.memory_service import format_memory_for_prompt, refresh_memory_after_turn
from backend.session_repo import (
    get_session_for_user,
    insert_message,
    list_messages_for_llm,
    touch_session,
    update_session_title,
)
from backend.trace import log_event
from backend.vision.chart_table_extract import enrich_last_user_message_with_vision

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    history: List[dict] = Field(default_factory=list)
    session_id: Optional[int] = None
    db_connection_id: Optional[int] = None
    multi_agents: bool = False


def _accumulate_assistant(acc: Dict[str, Any], event: Dict[str, Any]) -> None:
    et = event.get("type")
    if et == "thinking":
        acc.setdefault("thinking", []).append(str(event.get("content") or ""))
    elif et == "text":
        acc["content"] = acc.get("content", "") + str(event.get("content") or "")
    elif et == "chart":
        acc["chart"] = event.get("content")
    elif et == "kpi_cards":
        acc["kpiCards"] = event.get("content")
    elif et == "plan_summary":
        acc["planSummary"] = event.get("content")
    elif et == "error":
        acc["error"] = str(event.get("content") or "")


def _assistant_payload(acc: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    if acc.get("thinking"):
        out["thinking"] = acc["thinking"]
    if acc.get("chart") is not None:
        out["chart"] = acc["chart"]
    if acc.get("kpiCards") is not None:
        out["kpiCards"] = acc["kpiCards"]
    if acc.get("planSummary") is not None:
        out["planSummary"] = acc["planSummary"]
    if acc.get("error"):
        out["error"] = acc["error"]
    return out


def _session_title_from_message(message: str) -> str:
    collapsed = re.sub(r"\s+", " ", message).strip()
    return collapsed[:80] or "新对话"


def _next_disconnect_state(disconnected: bool, request_disconnected: bool) -> bool:
    if disconnected:
        return True
    return request_disconnected


@router.post("/chat")
async def chat(
    req: ChatRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
):
    trace_id = request_trace_id(request)
    skill_db = resolve_skill_db_env(req.db_connection_id)
    memory_block = format_memory_for_prompt(int(user["id"]))

    messages: List[Dict[str, str]]
    persist_sid: Optional[int] = None

    if req.session_id is not None:
        sess = get_session_for_user(req.session_id, int(user["id"]))
        if not sess:
            raise HTTPException(status_code=404, detail="会话不存在")
        prior = list_messages_for_llm(req.session_id)
        messages = prior + [{"role": "user", "content": req.message}]
        persist_sid = req.session_id
        try:
            insert_message(persist_sid, "user", req.message)
            update_session_title(
                persist_sid,
                int(user["id"]),
                _session_title_from_message(req.message),
            )
        except Exception as exc:
            log_event(
                trace_id,
                "http.chat",
                "session.persist_user_failed",
                str(exc),
                level="WARN",
            )
    else:
        messages = [
            *req.history,
            {"role": "user", "content": req.message},
        ]

    log_event(
        trace_id,
        "http.chat",
        "request.started",
        payload={
            "message_length": len(req.message),
            "history_count": len(req.history),
            "session_id": req.session_id,
            "multi_agents": req.multi_agents,
        },
    )

    messages = await enrich_last_user_message_with_vision(messages, trace_id)
    messages = augment_messages_for_upload_followup(messages)

    async def event_gen() -> AsyncGenerator[dict, None]:
        started_at = perf_counter()
        acc: Dict[str, Any] = {"content": "", "thinking": []}
        disconnected = False
        try:
            # call llm to get response. 
            async for event in stream_chat(
                messages,
                trace_id=trace_id,
                skill_db_overrides=skill_db,
                memory_block=memory_block or None,
                multi_agents=req.multi_agents,
            ):
                next_disconnected = _next_disconnect_state(
                    disconnected, await request.is_disconnected()
                )
                if next_disconnected and not disconnected:
                    log_event(trace_id, "http.chat", "request.disconnected", level="WARN")
                disconnected = next_disconnected
                _accumulate_assistant(acc, event)
                if disconnected:
                    continue
                log_event(
                    trace_id,
                    "http.chat",
                    "sse.event",
                    payload={"type": event.get("type")},
                )
                yield {
                    "event": "message",
                    "data": json.dumps(event, ensure_ascii=False),
                }
            log_event(
                trace_id,
                "http.chat",
                "request.completed",
                payload={"elapsed_ms": round((perf_counter() - started_at) * 1000, 2)},
            )
        except Exception as exc:
            log_event(trace_id, "http.chat", "request.failed", str(exc), level="ERROR")
            yield {
                "event": "message",
                "data": json.dumps({"type": "error", "content": str(exc)}, ensure_ascii=False),
            }
            yield {
                "event": "message",
                "data": json.dumps({"type": "done", "content": None}, ensure_ascii=False),
            }
            return
        finally:
            if persist_sid is not None:
                try:
                    insert_message(
                        persist_sid,
                        "assistant",
                        acc.get("content") or "",
                        _assistant_payload(acc) if _assistant_payload(acc) else None,
                    )
                    touch_session(persist_sid, int(user["id"]))
                    background_tasks.add_task(
                        refresh_memory_after_turn,
                        trace_id,
                        int(user["id"]),
                        persist_sid,
                        req.message,
                        acc.get("content") or "",
                    )
                except Exception as exc:
                    log_event(
                        trace_id,
                        "http.chat",
                        "session.persist_assistant_failed",
                        str(exc),
                        level="WARN",
                    )

    return EventSourceResponse(event_gen(), headers={"X-Trace-Id": trace_id})
