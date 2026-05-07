"""Session CRUD and message load for the chat UI."""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.auth_deps import get_current_user
from backend.memory_repo import suggested_prompts_for_user
from backend.session_repo import (
    create_session,
    delete_session,
    get_session_for_user,
    list_sessions,
    load_messages_ui,
    update_session_title,
)

router = APIRouter(prefix="/sessions", tags=["sessions"])


class SessionCreate(BaseModel):
    title: str = Field(default="新对话", max_length=255)


class SessionPatch(BaseModel):
    title: str = Field(..., max_length=255)


class SessionListResponse(BaseModel):
    sessions: List[dict]
    suggested_prompts: List[str]


class SessionCreateResponse(BaseModel):
    id: int
    suggested_prompts: List[str]


@router.get("", response_model=SessionListResponse)
def get_session_list(user: Dict[str, Any] = Depends(get_current_user)) -> dict:
    sessions = list_sessions(user["id"])
    prompts = suggested_prompts_for_user(user["id"])
    return {"sessions": sessions, "suggested_prompts": prompts}


@router.post("", response_model=SessionCreateResponse)
def post_session(
    body: SessionCreate, user: Dict[str, Any] = Depends(get_current_user)
) -> dict:
    sid = create_session(user["id"], body.title)
    prompts = suggested_prompts_for_user(user["id"])
    return {"id": sid, "suggested_prompts": prompts}


@router.get("/{session_id}/messages")
def get_messages(
    session_id: int, user: Dict[str, Any] = Depends(get_current_user)
) -> List[dict]:
    if not get_session_for_user(session_id, user["id"]):
        raise HTTPException(status_code=404, detail="会话不存在")
    return load_messages_ui(session_id)


@router.patch("/{session_id}")
def patch_session(
    session_id: int,
    body: SessionPatch,
    user: Dict[str, Any] = Depends(get_current_user),
) -> dict:
    if not get_session_for_user(session_id, user["id"]):
        raise HTTPException(status_code=404, detail="会话不存在")
    update_session_title(session_id, user["id"], body.title)
    return {"ok": True}


@router.delete("/{session_id}")
def remove_session(
    session_id: int, user: Dict[str, Any] = Depends(get_current_user)
) -> dict:
    if not get_session_for_user(session_id, user["id"]):
        raise HTTPException(status_code=404, detail="会话不存在")
    delete_session(session_id, user["id"])
    return {"ok": True}
