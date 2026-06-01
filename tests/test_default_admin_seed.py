from __future__ import annotations

from unittest.mock import Mock

from backend.config import Settings
from backend.default_admin_seed import seed_default_admin


def test_seed_default_admin_creates_missing_user(monkeypatch):
    create_user = Mock()
    monkeypatch.setattr("backend.default_admin_seed.get_by_username", Mock(return_value=None))
    monkeypatch.setattr("backend.default_admin_seed.create_user", create_user)
    monkeypatch.setattr("backend.default_admin_seed.hash_password", Mock(return_value="hashed"))

    result = seed_default_admin(
        Settings(
            default_admin_username="ops",
            default_admin_password="secret",
        )
    )

    assert result == "created"
    create_user.assert_called_once_with("ops", "hashed", "admin")


def test_seed_default_admin_keeps_existing_admin_password(monkeypatch):
    update_user = Mock()
    monkeypatch.setattr(
        "backend.default_admin_seed.get_by_username",
        Mock(return_value={"id": 7, "role": "admin", "is_active": 1}),
    )
    monkeypatch.setattr("backend.default_admin_seed.update_user", update_user)
    hash_password = Mock(return_value="hashed")
    monkeypatch.setattr("backend.default_admin_seed.hash_password", hash_password)

    result = seed_default_admin(
        Settings(
            default_admin_username="admin",
            default_admin_password="secret",
        )
    )

    assert result == "exists"
    update_user.assert_not_called()
    hash_password.assert_not_called()


def test_seed_default_admin_can_reset_existing_password(monkeypatch):
    update_user = Mock()
    monkeypatch.setattr(
        "backend.default_admin_seed.get_by_username",
        Mock(return_value={"id": 7, "role": "user", "is_active": 0}),
    )
    monkeypatch.setattr("backend.default_admin_seed.update_user", update_user)
    monkeypatch.setattr("backend.default_admin_seed.hash_password", Mock(return_value="hashed"))

    result = seed_default_admin(
        Settings(
            default_admin_username="admin",
            default_admin_password="secret",
            default_admin_reset_password=True,
        )
    )

    assert result == "updated"
    update_user.assert_called_once_with(
        7,
        password_hash="hashed",
        role="admin",
        is_active=True,
    )


def test_seed_default_admin_skips_empty_config(monkeypatch):
    get_by_username = Mock()
    monkeypatch.setattr("backend.default_admin_seed.get_by_username", get_by_username)

    result = seed_default_admin(
        Settings(
            default_admin_username="",
            default_admin_password="",
        )
    )

    assert result == "skipped"
    get_by_username.assert_not_called()
