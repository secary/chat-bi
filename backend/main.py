from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from typing import AsyncGenerator, List

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from backend.agent.runner import stream_chat

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


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    original_name = file.filename or "upload"
    suffix = Path(original_name).suffix.lower()
    if suffix not in ALLOWED_UPLOAD_SUFFIXES:
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
        raise HTTPException(status_code=400, detail="上传文件为空")

    return UploadResult(filename=original_name, server_path=str(target), size=size)


@app.post("/chat")
async def chat(req: ChatRequest, request: Request):
    messages = [
        *req.history,
        {"role": "user", "content": req.message},
    ]

    async def event_gen() -> AsyncGenerator[dict, None]:
        try:
            async for event in stream_chat(messages):
                if await request.is_disconnected():
                    break
                yield {
                    "event": "message",
                    "data": json.dumps(event, ensure_ascii=False),
                }
        except Exception as exc:
            yield {
                "event": "message",
                "data": json.dumps({"type": "error", "content": str(exc)}, ensure_ascii=False),
            }
            yield {
                "event": "message",
                "data": json.dumps({"type": "done", "content": None}, ensure_ascii=False),
            }

    return EventSourceResponse(event_gen())
