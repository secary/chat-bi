"""SSE /chat with optional session persistence."""

from __future__ import annotations

import json
import re
from time import perf_counter
from typing import Any, AsyncGenerator, Dict, List, Literal, Optional, Union

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
    DEFAULT_SESSION_TITLE,
    get_session_for_user,
    is_default_session_title,
    insert_message,
    list_messages_for_llm,
    touch_session,
    update_session_title,
)
from backend.agent.abort_state import clear_abort, get_abort_event, is_aborted
from backend.trace import log_event

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    history: List[dict] = Field(default_factory=list)
    uploads: List[dict] = Field(default_factory=list)
    session_id: Optional[int] = None
    db_connection_id: Optional[int] = None
    multi_agents: Union[bool, Literal["auto", "single"]] = "auto"


@router.post("/abort")
async def abort_chat(
    request: Request,
    user: dict = Depends(get_current_user),
):
    """Abort an in-progress chat request by trace_id."""
    trace_id = request_trace_id(request)
    get_abort_event(trace_id).set()
    log_event(trace_id, "http.chat", "abort.requested", level="INFO")
    return {"status": "aborted", "trace_id": trace_id}


def _accumulate_assistant(acc: Dict[str, Any], event: Dict[str, Any]) -> None:
    et = event.get("type")
    if et == "thinking":
        content = event.get("content")
        if isinstance(content, (dict, str)):
            acc.setdefault("thinking", []).append(content)
        else:
            acc.setdefault("thinking", []).append(str(content or ""))
    elif et == "text":
        acc["content"] = acc.get("content", "") + str(event.get("content") or "")
    elif et == "chart":
        acc["chart"] = event.get("content")
    elif et == "kpi_cards":
        acc["kpiCards"] = event.get("content")
    elif et == "plan_summary":
        acc["planSummary"] = event.get("content")
    elif et == "analysis_proposal":
        acc["analysisProposal"] = event.get("content")
    elif et == "dashboard_ready":
        acc["dashboardReady"] = event.get("content")
    elif et == "error":
        acc["error"] = str(event.get("content") or "")
    elif et == "done":
        content = event.get("content")
        if isinstance(content, dict) and content.get("elapsed_ms") is not None:
            acc["elapsedMs"] = content["elapsed_ms"]


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
    if acc.get("analysisProposal") is not None:
        out["analysisProposal"] = acc["analysisProposal"]
    if acc.get("dashboardReady") is not None:
        out["dashboardReady"] = acc["dashboardReady"]
    if acc.get("error"):
        out["error"] = acc["error"]
    if acc.get("elapsedMs") is not None:
        out["elapsedMs"] = acc["elapsedMs"]
    return out


def _session_title_from_message(message: str) -> str:
    collapsed = re.sub(r"\s+", " ", message).strip()
    title = _compact_session_title(collapsed)
    return title or DEFAULT_SESSION_TITLE


def _compact_session_title(message: str) -> str:
    text = re.sub(r"/tmp/chatbi-uploads/[A-Za-z0-9._-]+", "上传文件", message).strip()
    if not text:
        return ""
    if "上传文件" in text and ("校验" in text or "结构" in text):
        return "上传文件结构校验"

    for _ in range(4):
        next_text = re.sub(
            r"^(?:请|麻烦|帮我|帮忙|给我|能不能|可以|我想|想|看下|看看|查询一下|查一下|查|"
            r"统计一下|统计|分析一下|分析|对比一下|对比|说明一下|说明|告诉我)"
            r"[\s，,。:：]*",
            "",
            text,
        ).strip()
        if next_text == text:
            break
        text = next_text

    text = re.split(r"(?:，|,|；|;|\s)+(?:并|然后|顺便|同时)", text, maxsplit=1)[0]
    text = re.sub(r"[？?。.!！\s]+$", "", text).strip()
    text = re.sub(r"(?:可以吗|好吗|怎么样|是什么|如何)$", "", text).strip()
    text = re.sub(r"[，,；;：:\s]+$", "", text).strip()
    return text[:24]


def _should_auto_update_session_title(
    current_title: str, prior_messages: List[Dict[str, Any]]
) -> bool:
    if not is_default_session_title(current_title):
        return False
    return not prior_messages


def _next_disconnect_state(disconnected: bool, request_disconnected: bool) -> bool:
    if disconnected:
        return True
    return request_disconnected


def _message_with_upload_context(message: str, uploads: List[dict]) -> str:
    if not uploads:
        return message
    lines = [
        "[ChatBI 附件上下文：用户已上传以下附件。若当前问题涉及附件内容，必须优先使用这些路径处理；不要把路径暴露给用户。]"
    ]
    for item in uploads:
        server_path = str(item.get("server_path") or "").strip()
        if not server_path:
            continue
        filename = str(item.get("filename") or server_path.rsplit("/", 1)[-1])
        lines.append(
            f"- 数据文件：{filename}；路径：{server_path}；如问题涉及文件，先校验结构；"
            "符合现有业务表就直接分析，不符合就按通用表分析。"
        )
    if len(lines) == 1:
        return message
    return "\n".join(lines) + "\n\n" + message


@router.post("/chat")
async def chat(
    req: ChatRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
):
    trace_id = request_trace_id(request)
    # Create abort event for this trace_id before processing
    get_abort_event(trace_id)
    skill_db = resolve_skill_db_env(req.db_connection_id)
    memory_block = format_memory_for_prompt(int(user["id"]), exclude_session_id=req.session_id)

    messages: List[Dict[str, str]]
    persist_sid: Optional[int] = None

    if req.session_id is not None:
        sess = get_session_for_user(req.session_id, int(user["id"]))
        if not sess:
            raise HTTPException(status_code=404, detail="会话不存在")
        prior = list_messages_for_llm(req.session_id, user_id=int(user["id"]))
        user_content_for_agent = _message_with_upload_context(req.message, req.uploads)
        messages = prior + [{"role": "user", "content": user_content_for_agent}]
        persist_sid = req.session_id
        try:
            user_payload = {"uploads": req.uploads} if req.uploads else None
            insert_message(persist_sid, "user", req.message, user_payload)
            if _should_auto_update_session_title(str(sess.get("title") or ""), prior):
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
        user_content_for_agent = _message_with_upload_context(req.message, req.uploads)
        messages = [
            *req.history,
            {"role": "user", "content": user_content_for_agent},
        ]

    log_event(
        trace_id,
        "http.chat",
        "request.started",
        payload={
            "message_length": len(req.message),
            "history_count": len(req.history),
            "session_id": req.session_id,
            "upload_count": len(req.uploads),
            "multi_agents": req.multi_agents,
        },
    )

    messages = augment_messages_for_upload_followup(messages)

    async def event_gen() -> AsyncGenerator[dict, None]:
        started_at = perf_counter()
        acc: Dict[str, Any] = {"content": "", "thinking": []}
        disconnected = False
        nonlocal messages

        try:
            # call llm to get response.
            async for event in stream_chat(
                messages,
                trace_id=trace_id,
                skill_db_overrides=skill_db,
                memory_block=memory_block or None,
                multi_agents=req.multi_agents,
                session_id=persist_sid,
                user_id=int(user["id"]),
            ):
                next_disconnected = _next_disconnect_state(
                    disconnected, await request.is_disconnected()
                )
                if next_disconnected and not disconnected:
                    log_event(trace_id, "http.chat", "request.disconnected", level="WARN")
                disconnected = next_disconnected
                if event.get("type") == "done":
                    event = {
                        **event,
                        "content": {"elapsed_ms": round((perf_counter() - started_at) * 1000, 2)},
                    }
                _accumulate_assistant(acc, event)
                if not disconnected:
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
                if disconnected or is_aborted(trace_id):
                    if is_aborted(trace_id) and not disconnected:
                        log_event(
                            trace_id,
                            "http.chat",
                            "sse.abort_stop_consumer",
                            level="INFO",
                        )
                    break
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
            # Clean up abort flag on completion
            clear_abort(trace_id)

    # turn every stream_chat content into sse event.
    # it will turn yield contents into  text/event-stream
    # each data is a json string
    return EventSourceResponse(event_gen(), headers={"X-Trace-Id": trace_id})
