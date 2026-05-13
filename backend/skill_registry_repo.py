"""skill_registry: per-skill enable/disable without deleting files."""

from __future__ import annotations

from typing import Set

from backend.db_tables import SKILL_REGISTRY
from backend.db_mysql import admin_execute, admin_fetch_all


def disabled_slugs() -> Set[str]:
    try:
        rows = admin_fetch_all(
            f"SELECT skill_slug FROM {SKILL_REGISTRY} WHERE enabled = 0",
        )
        return {str(r["skill_slug"]) for r in rows}
    except Exception:
        return set()


def set_enabled(skill_slug: str, enabled: bool) -> None:
    admin_execute(
        f"INSERT INTO {SKILL_REGISTRY} (skill_slug, enabled) VALUES (%s, %s) "
        "ON DUPLICATE KEY UPDATE enabled = VALUES(enabled)",
        (skill_slug, int(enabled)),
    )
