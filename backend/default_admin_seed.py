"""Seed configured application users."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal

from backend.auth_password import hash_password
from backend.config import Settings, settings
from backend.user_repo import create_user, get_by_username, update_user

logger = logging.getLogger(__name__)
SeedResult = Literal["created", "updated", "exists", "skipped", "failed"]


@dataclass(frozen=True)
class SeedUser:
    username: str
    password: str
    role: str = "user"


def _normalize_role(role: str) -> str:
    value = role.strip().lower()
    return value if value in ("admin", "user") else "user"


def parse_seed_users(raw: str) -> list[SeedUser]:
    """Parse CHATBI_SEED_USERS as username:password:role;username2:password2:role."""
    users: list[SeedUser] = []
    seen: set[str] = set()
    for item in raw.split(";"):
        item = item.strip()
        if not item:
            continue
        parts = [part.strip() for part in item.split(":", 2)]
        if len(parts) < 2:
            logger.warning("Seed user skipped because entry is malformed: %s", item)
            continue
        username, password = parts[0], parts[1]
        role = _normalize_role(parts[2]) if len(parts) == 3 else "user"
        if not username or not password:
            logger.warning("Seed user skipped because username or password is empty.")
            continue
        if username in seen:
            logger.warning("Seed user skipped because username is duplicated: %s", username)
            continue
        seen.add(username)
        users.append(SeedUser(username=username, password=password, role=role))
    return users


def _seed_user(
    username: str,
    password: str,
    role: str,
    *,
    reset_password: bool,
    label: str,
) -> SeedResult:
    if not username or not password:
        logger.info("%s seed skipped because username or password is empty.", label)
        return "skipped"

    try:
        row = get_by_username(username)
        if not row:
            create_user(username, hash_password(password), role)
            logger.info("%s user seeded: %s", label, username)
            return "created"

        existing_role = str(row.get("role") or "")
        is_active = bool(row.get("is_active"))
        password_hash = hash_password(password) if reset_password else None
        if existing_role == role and is_active and password_hash is None:
            return "exists"

        update_user(
            int(row["id"]),
            password_hash=password_hash,
            role=role if existing_role != role else None,
            is_active=True if not is_active else None,
        )
        logger.info("%s user normalized: %s", label, username)
        return "updated"
    except Exception:
        logger.exception("%s user seed failed: %s", label, username)
        return "failed"


def _seed_configured_user_list(
    users: list[SeedUser],
    current_settings: Settings,
) -> list[SeedResult]:
    results: list[SeedResult] = []
    for user in users:
        results.append(
            _seed_user(
                user.username,
                user.password,
                user.role,
                reset_password=current_settings.seed_users_reset_password,
                label="Configured seed",
            )
        )
    return results


def seed_configured_users(current_settings: Settings = settings) -> list[SeedResult]:
    """Create or normalize additional app users from CHATBI_SEED_USERS."""
    return _seed_configured_user_list(
        parse_seed_users(current_settings.seed_users_raw),
        current_settings,
    )


def seed_startup_users(current_settings: Settings = settings) -> list[SeedResult]:
    """Seed all users configured for application startup."""
    configured_users = parse_seed_users(current_settings.seed_users_raw)
    return _seed_configured_user_list(configured_users, current_settings)
