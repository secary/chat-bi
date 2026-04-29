from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from time import perf_counter
from typing import AsyncGenerator, List

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from backend.agent.runner import stream_chat
from backend.trace import log_event

load_dotenv()

app = FastAPI(title="ChatBI API", version="0.1.0")
UPLOAD_DIR = Path("/tmp/chatbi-uploads")
ALLOWED_UPLOAD_SUFFIXES = {".csv", ".xlsx", ".xlsm"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    history: List[dict] = []


class UploadResult(BaseModel):
    filename: str
    server_path: str
    size: int
    trace_id: str


@app.get("/health")
async def health():
    return {"status": "ok"}


def request_trace_id(request: Request) -> str:
    incoming = request.headers.get("x-trace-id", "").strip()
    if incoming and re.fullmatch(r"[0-9A-Za-z._:-]{8,64}", incoming):
        return incoming
    return uuid.uuid4().hex


@app.post("/upload")
async def upload(request: Request, file: UploadFile = File(...)):
    trace_id = request_trace_id(request)
    started_at = perf_counter()
    original_name = file.filename or "upload"
    log_event(
        trace_id,
        "http.upload",
        "request.started",
        payload={"filename": original_name, "content_type": file.content_type},
    )
    suffix = Path(original_name).suffix.lower()
    if suffix not in ALLOWED_UPLOAD_SUFFIXES:
        log_event(
            trace_id,
            "http.upload",
            "request.rejected",
            "unsupported suffix",
            {"suffix": suffix},
            "WARN",
        )
        raise HTTPException(status_code=400, detail="仅支持 CSV 或 Excel 文件")

    safe_stem = re.sub(r"[^0-9A-Za-z._-]+", "_", Path(original_name).stem).strip("._")
    if not safe_stem:
        safe_stem = "upload"
    target = UPLOAD_DIR / f"{uuid.uuid4().hex}_{safe_stem}{suffix}"
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    size = 0
    with target.open("wb") as handle:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            handle.write(chunk)
    await file.close()

    if size == 0:
        target.unlink(missing_ok=True)
        log_event(trace_id, "http.upload", "request.rejected", "empty file", level="WARN")
        raise HTTPException(status_code=400, detail="上传文件为空")

    log_event(
        trace_id,
        "http.upload",
        "request.completed",
        payload={
            "server_path": str(target),
            "size": size,
            "elapsed_ms": round((perf_counter() - started_at) * 1000, 2),
        },
    )
    return UploadResult(
        filename=original_name,
        server_path=str(target),
        size=size,
        trace_id=trace_id,
    )


@app.post("/chat")
async def chat(req: ChatRequest, request: Request):
    trace_id = request_trace_id(request)
    messages = [
        *req.history,
        {"role": "user", "content": req.message},
    ]
    log_event(
        trace_id,
        "http.chat",
        "request.started",
        payload={"message_length": len(req.message), "history_count": len(req.history)},
    )

    async def event_gen() -> AsyncGenerator[dict, None]:
        started_at = perf_counter()
        try:
            async for event in stream_chat(messages, trace_id=trace_id):
                if await request.is_disconnected():
                    log_event(trace_id, "http.chat", "request.disconnected", level="WARN")
                    break
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

    return EventSourceResponse(event_gen(), headers={"X-Trace-Id": trace_id})
