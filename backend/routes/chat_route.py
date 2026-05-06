"""SSE /chat with optional session persistence."""

from __future__ import annotations

import json
from time import perf_counter
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from backend.agent.runner import stream_chat
from backend.connection_repo import resolve_skill_db_env
from backend.http_utils import request_trace_id
from backend.session_repo import (
    get_session,
    insert_message,
    list_messages_for_llm,
    touch_session,
    update_session_title,
)
from backend.trace import log_event

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    history: List[dict] = Field(default_factory=list)
    session_id: Optional[int] = None
    db_connection_id: Optional[int] = None


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
    if acc.get("error"):
        out["error"] = acc["error"]
    return out


@router.post("/chat")
async def chat(req: ChatRequest, request: Request):
    trace_id = request_trace_id(request)
    skill_db = resolve_skill_db_env(req.db_connection_id)

    messages: List[Dict[str, str]]
    persist_sid: Optional[int] = None

    if req.session_id is not None:
        sess = get_session(req.session_id)
        if not sess:
            raise HTTPException(status_code=404, detail="会话不存在")
        prior = list_messages_for_llm(req.session_id)
        messages = prior + [{"role": "user", "content": req.message}]
        persist_sid = req.session_id
        try:
            insert_message(persist_sid, "user", req.message)
            if not prior and (sess.get("title") == "新对话" or sess.get("title") == ""):
                update_session_title(
                    persist_sid,
                    (req.message.strip()[:80] or "新对话"),
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
        },
    )

    async def event_gen() -> AsyncGenerator[dict, None]:
        started_at = perf_counter()
        acc: Dict[str, Any] = {"content": "", "thinking": []}
        try:
            async for event in stream_chat(
                messages,
                trace_id=trace_id,
                skill_db_overrides=skill_db,
            ):
                if await request.is_disconnected():
                    log_event(
                        trace_id, "http.chat", "request.disconnected", level="WARN"
                    )
                    break
                _accumulate_assistant(acc, event)
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
                "data": json.dumps(
                    {"type": "error", "content": str(exc)}, ensure_ascii=False
                ),
            }
            yield {
                "event": "message",
                "data": json.dumps(
                    {"type": "done", "content": None}, ensure_ascii=False
                ),
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
                    touch_session(persist_sid)
                except Exception as exc:
                    log_event(
                        trace_id,
                        "http.chat",
                        "session.persist_assistant_failed",
                        str(exc),
                        level="WARN",
                    )

    return EventSourceResponse(event_gen(), headers={"X-Trace-Id": trace_id})
