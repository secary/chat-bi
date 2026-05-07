"""JWT access tokens."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import jwt

from backend.config import settings


def create_access_token(user_id: int, role: str) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(hours=settings.jwt_exp_hours)
    payload: Dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": exp,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_access_token(token: str) -> Dict[str, Any]:
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
