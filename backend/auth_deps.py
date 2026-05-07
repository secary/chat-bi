"""FastAPI dependencies: JWT user and admin guard."""

from __future__ import annotations

from typing import Any, Dict

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.auth_tokens import decode_access_token
from backend.config import settings
from backend.user_repo import get_by_id

_bearer = HTTPBearer(auto_error=False)


def _row_to_user(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": int(row["id"]),
        "username": str(row["username"]),
        "role": str(row["role"]),
    }


def _user_from_token(token: str) -> Dict[str, Any] | None:
    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError:
        return None
    sub = payload.get("sub")
    if sub is None:
        return None
    try:
        uid = int(sub)
    except (TypeError, ValueError):
        return None
    row = get_by_id(uid)
    if not row or not row.get("is_active"):
        return None
    return _row_to_user(row)


def _fallback_dev_user() -> Dict[str, Any]:
    row = get_by_id(settings.auth_dev_user_id)
    if not row or not row.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="开发免登录模式需要数据库中存在默认用户（见 CHATBI_AUTH_DEV_USER_ID）",
        )
    return _row_to_user(row)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> Dict[str, Any]:
    if settings.auth_enabled:
        if credentials is None or not credentials.credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="未登录或缺少 Authorization Bearer",
            )
        user = _user_from_token(credentials.credentials)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效或过期的令牌",
            )
        return user

    if credentials and credentials.credentials:
        user = _user_from_token(credentials.credentials)
        if user is not None:
            return user

    return _fallback_dev_user()


def require_admin(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )
    return user
