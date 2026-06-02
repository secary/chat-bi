from __future__ import annotations

from unittest.mock import Mock

from backend.config import Settings
from backend.default_admin_seed import (
    parse_seed_users,
    seed_configured_users,
    seed_startup_users,
)


def test_parse_seed_users_supports_multiple_users():
    users = parse_seed_users("secary:pass1:admin; analyst:pass2:user; viewer:pass3")

    assert [(u.username, u.password, u.role) for u in users] == [
        ("secary", "pass1", "admin"),
        ("analyst", "pass2", "user"),
        ("viewer", "pass3", "user"),
    ]


def test_parse_seed_users_skips_invalid_and_duplicate_entries():
    users = parse_seed_users("bad; alice::admin; bob:pass:owner; bob:second:admin")

    assert [(u.username, u.password, u.role) for u in users] == [
        ("bob", "pass", "user"),
    ]


def test_seed_configured_users_creates_missing_users(monkeypatch):
    create_user = Mock()
    monkeypatch.setattr("backend.default_admin_seed.get_by_username", Mock(return_value=None))
    monkeypatch.setattr("backend.default_admin_seed.create_user", create_user)
    monkeypatch.setattr("backend.default_admin_seed.hash_password", Mock(return_value="hashed"))

    result = seed_configured_users(
        Settings(
            seed_users_raw="secary:secret:admin;analyst:secret2:user",
        )
    )

    assert result == ["created", "created"]
    create_user.assert_any_call("secary", "hashed", "admin")
    create_user.assert_any_call("analyst", "hashed", "user")


def test_seed_configured_users_normalizes_existing_user_without_password_reset(monkeypatch):
    update_user = Mock()
    monkeypatch.setattr(
        "backend.default_admin_seed.get_by_username",
        Mock(return_value={"id": 9, "role": "user", "is_active": 0}),
    )
    monkeypatch.setattr("backend.default_admin_seed.update_user", update_user)
    hash_password = Mock(return_value="hashed")
    monkeypatch.setattr("backend.default_admin_seed.hash_password", hash_password)

    result = seed_configured_users(
        Settings(
            seed_users_raw="secary:secret:admin",
        )
    )

    assert result == ["updated"]
    update_user.assert_called_once_with(
        9,
        password_hash=None,
        role="admin",
        is_active=True,
    )
    hash_password.assert_not_called()


def test_seed_startup_users_seeds_configured_users(monkeypatch):
    create_user = Mock()
    monkeypatch.setattr("backend.default_admin_seed.get_by_username", Mock(return_value=None))
    monkeypatch.setattr("backend.default_admin_seed.create_user", create_user)
    monkeypatch.setattr("backend.default_admin_seed.hash_password", Mock(return_value="hashed"))

    result = seed_startup_users(
        Settings(
            seed_users_raw="ops:ops-secret:admin;demo:demo-secret:user",
        )
    )

    assert result == ["created", "created"]
    create_user.assert_any_call("ops", "hashed", "admin")
    create_user.assert_any_call("demo", "hashed", "user")
    assert create_user.call_count == 2


def test_seed_startup_users_skips_when_seed_users_empty(monkeypatch):
    get_by_username = Mock()
    monkeypatch.setattr("backend.default_admin_seed.get_by_username", get_by_username)

    result = seed_startup_users(Settings(seed_users_raw=""))

    assert result == []
    get_by_username.assert_not_called()
