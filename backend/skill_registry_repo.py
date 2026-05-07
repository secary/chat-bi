"""skill_registry: per-skill enable/disable without deleting files."""

from __future__ import annotations

from typing import Set

from backend.db_mysql import admin_execute, admin_fetch_all


def disabled_slugs() -> Set[str]:
    try:
        rows = admin_fetch_all(
            "SELECT skill_slug FROM skill_registry WHERE enabled = 0",
        )
        return {str(r["skill_slug"]) for r in rows}
    except Exception:
        return set()


def set_enabled(skill_slug: str, enabled: bool) -> None:
    admin_execute(
        "INSERT INTO skill_registry (skill_slug, enabled) VALUES (%s, %s) "
        "ON DUPLICATE KEY UPDATE enabled = VALUES(enabled)",
        (skill_slug, int(enabled)),
    )
