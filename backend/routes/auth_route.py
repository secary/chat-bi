"""Login and current user."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.auth_deps import get_current_user
from backend.auth_password import verify_password
from backend.auth_tokens import create_access_token
from backend.user_repo import get_by_username

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginBody(BaseModel):
    username: str = Field(..., min_length=1, max_length=120)
    password: str = Field(..., min_length=1, max_length=256)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=TokenResponse)
def login(body: LoginBody) -> Dict[str, Any]:
    row = get_by_username(body.username.strip())
    if not row or not row.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )
    if not verify_password(body.password, str(row["password_hash"] or "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )
    token = create_access_token(int(row["id"]), str(row["role"]))
    return {"access_token": token, "token_type": "bearer"}


class MeResponse(BaseModel):
    id: int
    username: str
    role: str


@router.get("/me", response_model=MeResponse)
def me(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    return {"id": user["id"], "username": user["username"], "role": user["role"]}
