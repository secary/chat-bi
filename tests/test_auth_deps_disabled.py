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
        lambda uid: {
            "id": 1,
            "username": "admin",
            "role": "admin",
            "is_active": 1,
        }
        if uid == 1
        else None,
    )

    user = auth_deps.get_current_user(credentials=None)

    assert user["id"] == 1
    assert user["username"] == "admin"
    assert user["role"] == "admin"


def test_get_current_user_auth_on_requires_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_settings = MagicMock()
    mock_settings.auth_enabled = True
    monkeypatch.setattr(auth_deps, "settings", mock_settings)

    with pytest.raises(HTTPException) as exc:
        auth_deps.get_current_user(credentials=None)
    assert exc.value.status_code == 401
