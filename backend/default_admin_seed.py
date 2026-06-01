"""Seed the configured default admin user."""

from __future__ import annotations

import logging
from typing import Literal

from backend.auth_password import hash_password
from backend.config import Settings, settings
from backend.user_repo import create_user, get_by_username, update_user

logger = logging.getLogger(__name__)
SeedResult = Literal["created", "updated", "exists", "skipped", "failed"]


def seed_default_admin(current_settings: Settings = settings) -> SeedResult:
    """Create or normalize the default admin user from environment settings."""
    username = current_settings.default_admin_username.strip()
    password = current_settings.default_admin_password
    if not username or not password:
        logger.info("Default admin seed skipped because username or password is empty.")
        return "skipped"

    try:
        row = get_by_username(username)
        if not row:
            create_user(username, hash_password(password), "admin")
            logger.info("Default admin user seeded: %s", username)
            return "created"

        role = str(row.get("role") or "")
        is_active = bool(row.get("is_active"))
        password_hash = (
            hash_password(password) if current_settings.default_admin_reset_password else None
        )
        if role == "admin" and is_active and password_hash is None:
            return "exists"

        update_user(
            int(row["id"]),
            password_hash=password_hash,
            role="admin" if role != "admin" else None,
            is_active=True if not is_active else None,
        )
        logger.info("Default admin user normalized: %s", username)
        return "updated"
    except Exception:
        logger.exception("Default admin seed failed.")
        return "failed"
