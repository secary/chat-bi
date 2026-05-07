"""Login and current user."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from backend.auth_deps import get_current_user
from backend.auth_password import verify_password
from backend.auth_tokens import create_access_token
from backend.http_utils import request_trace_id
from backend.trace import log_event
from backend.user_repo import get_by_username

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginBody(BaseModel):
    username: str = Field(..., min_length=1, max_length=120)
    password: str = Field(..., min_length=1, max_length=256)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=TokenResponse)
def login(body: LoginBody, request: Request) -> Dict[str, Any]:
    trace_id = request_trace_id(request)
    username = body.username.strip()
    log_event(
        trace_id,
        "auth.login",
        "started",
        payload={"username": username},
    )
    row = get_by_username(username)
    if not row or not row.get("is_active"):
        log_event(
            trace_id,
            "auth.login",
            "failed",
            "invalid username or inactive user",
            payload={"username": username},
            level="WARN",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )
    if not verify_password(body.password, str(row["password_hash"] or "")):
        log_event(
            trace_id,
            "auth.login",
            "failed",
            "invalid password",
            payload={"username": username, "user_id": int(row["id"])},
            level="WARN",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )
    token = create_access_token(int(row["id"]), str(row["role"]))
    log_event(
        trace_id,
        "auth.login",
        "completed",
        payload={"user_id": int(row["id"]), "username": username, "role": str(row["role"])},
    )
    return {"access_token": token, "token_type": "bearer"}


class MeResponse(BaseModel):
    id: int
    username: str
    role: str


@router.get("/me", response_model=MeResponse)
def me(request: Request, user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    log_event(
        request_trace_id(request),
        "auth.me",
        "viewed",
        payload={"user_id": int(user["id"]), "username": user["username"], "role": user["role"]},
    )
    return {"id": user["id"], "username": user["username"], "role": user["role"]}
