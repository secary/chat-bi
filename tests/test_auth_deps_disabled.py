"""auth_deps 在 CHATBI_AUTH_ENABLED=off 时的行为。"""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from backend import auth_deps


def test_get_current_user_auth_off_uses_dev_user(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_settings = MagicMock()
    mock_settings.auth_enabled = False
    mock_settings.auth_dev_user_id = 1
    monkeypatch.setattr(auth_deps, "settings", mock_settings)
    monkeypatch.setattr(
        auth_deps,
        "get_by_id",
        lambda uid: (
            {
                "id": 1,
                "username": "admin",
                "role": "admin",
                "is_active": 1,
            }
            if uid == 1
            else None
        ),
    )

    user = auth_deps.get_current_user(credentials=None)

    assert user["id"] == 1
    assert user["username"] == "admin"
    assert user["role"] == "admin"


def test_fallback_prefers_seed_admin_when_dev_id_not_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_settings = MagicMock()
    mock_settings.auth_enabled = False
    mock_settings.auth_dev_user_id = 2
    monkeypatch.setattr(auth_deps, "settings", mock_settings)

    def fake_get_by_id(uid: int):
        if uid == 2:
            return {
                "id": 2,
                "username": "bob",
                "role": "user",
                "is_active": 1,
            }
        return None

    def fake_get_by_username(name: str):
        if name == "admin":
            return {
                "id": 1,
                "username": "admin",
                "role": "admin",
                "is_active": 1,
            }
        return None

    monkeypatch.setattr(auth_deps, "get_by_id", fake_get_by_id)
    monkeypatch.setattr(auth_deps, "get_by_username", fake_get_by_username)

    user = auth_deps.get_current_user(credentials=None)

    assert user["id"] == 1
    assert user["role"] == "admin"


def test_get_current_user_auth_on_requires_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_settings = MagicMock()
    mock_settings.auth_enabled = True
    monkeypatch.setattr(auth_deps, "settings", mock_settings)

    with pytest.raises(HTTPException) as exc:
        auth_deps.get_current_user(credentials=None)
    assert exc.value.status_code == 401
