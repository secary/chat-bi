"""Password hashing with bcrypt via passlib."""

from __future__ import annotations

from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)


def verify_password(plain: str, password_hash: str) -> bool:
    if not plain or not password_hash:
        return False
    return _pwd_context.verify(plain, password_hash)
