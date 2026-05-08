"""skill_registry repo tolerates missing MySQL table during rollout."""

from __future__ import annotations

import pytest

from backend.skill_registry_repo import disabled_slugs


def test_disabled_slugs_returns_empty_on_query_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*_a, **_k):
        raise RuntimeError("no such table")

    monkeypatch.setattr("backend.skill_registry_repo.admin_fetch_all", boom)
    assert disabled_slugs() == set()
