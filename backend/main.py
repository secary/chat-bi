from __future__ import annotations

import json
from typing import AsyncGenerator, List

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from backend.agent.runner import stream_chat

load_dotenv()

app = FastAPI(title="ChatBI API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    history: List[dict] = []


@app.get("/health")
async def health():
    return {"status": "ok"}


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
