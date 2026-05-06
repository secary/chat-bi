"""Session CRUD and message load for the chat UI."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.session_repo import (
    create_session,
    delete_session,
    get_session,
    list_sessions,
    load_messages_ui,
    update_session_title,
)

router = APIRouter(prefix="/sessions", tags=["sessions"])


class SessionCreate(BaseModel):
    title: str = Field(default="新对话", max_length=255)


class SessionPatch(BaseModel):
    title: str = Field(..., max_length=255)


@router.get("")
def get_session_list() -> List[dict]:
    return list_sessions()


@router.post("")
def post_session(body: SessionCreate) -> dict:
    sid = create_session(body.title)
    return {"id": sid}


@router.get("/{session_id}/messages")
def get_messages(session_id: int) -> List[dict]:
    if not get_session(session_id):
        raise HTTPException(status_code=404, detail="会话不存在")
    return load_messages_ui(session_id)


@router.patch("/{session_id}")
def patch_session(session_id: int, body: SessionPatch) -> dict:
    if not get_session(session_id):
        raise HTTPException(status_code=404, detail="会话不存在")
    update_session_title(session_id, body.title)
    return {"ok": True}


@router.delete("/{session_id}")
def remove_session(session_id: int) -> dict:
    if not get_session(session_id):
        raise HTTPException(status_code=404, detail="会话不存在")
    delete_session(session_id)
    return {"ok": True}
