from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from backend.routes import admin_users_route as route


@pytest.fixture(autouse=True)
def quiet_route_logging(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(route, "request_trace_id", lambda _request: "trace-test")
    monkeypatch.setattr(route, "log_event", Mock())


def _request() -> SimpleNamespace:
    return SimpleNamespace()


def _admin(user_id: int = 2, username: str = "ops") -> dict:
    return {"id": user_id, "username": username, "role": "admin"}


def _root() -> dict:
    return {"id": 1, "username": "root", "role": "root"}


def test_non_root_admin_cannot_create_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(route, "get_by_username", Mock(return_value=None))

    with pytest.raises(HTTPException) as exc:
        route.post_user(
            route.UserCreate(username="ops2", password="secret", role="admin"),
            _request(),
            _admin(),
        )

    assert exc.value.status_code == 403


def test_root_username_is_reserved_for_seeded_super_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(route, "get_by_username", Mock(return_value=None))

    with pytest.raises(HTTPException) as exc:
        route.post_user(
            route.UserCreate(username="root", password="secret", role="admin"),
            _request(),
            _root(),
        )

    assert exc.value.status_code == 400


def test_root_role_cannot_be_created(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(route, "get_by_username", Mock(return_value=None))

    with pytest.raises(HTTPException) as exc:
        route.post_user(
            route.UserCreate(username="another-root", password="secret", role="root"),
            _request(),
            _root(),
        )

    assert exc.value.status_code == 400


def test_root_role_and_status_are_immutable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        route,
        "get_by_id",
        Mock(return_value={"id": 1, "username": "root", "role": "root", "is_active": 1}),
    )

    with pytest.raises(HTTPException) as exc:
        route.patch_user(
            1,
            route.UserPatch(role="user"),
            _request(),
            _root(),
        )

    assert exc.value.status_code == 400


def test_root_role_cannot_be_granted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        route,
        "get_by_id",
        Mock(return_value={"id": 4, "username": "analyst", "role": "user", "is_active": 1}),
    )

    with pytest.raises(HTTPException) as exc:
        route.patch_user(
            4,
            route.UserPatch(role="root"),
            _request(),
            _root(),
        )

    assert exc.value.status_code == 400


def test_non_root_admin_cannot_manage_other_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        route,
        "get_by_id",
        Mock(return_value={"id": 3, "username": "other-admin", "role": "admin", "is_active": 1}),
    )

    with pytest.raises(HTTPException) as exc:
        route.patch_user(
            3,
            route.UserPatch(password="new-secret"),
            _request(),
            _admin(),
        )

    assert exc.value.status_code == 403


def test_root_can_manage_administrators(monkeypatch: pytest.MonkeyPatch) -> None:
    update_user = Mock()
    monkeypatch.setattr(
        route,
        "get_by_id",
        Mock(return_value={"id": 3, "username": "ops", "role": "admin", "is_active": 1}),
    )
    monkeypatch.setattr(route, "update_user", update_user)

    result = route.patch_user(
        3,
        route.UserPatch(role="user"),
        _request(),
        _root(),
    )

    assert result == {"ok": True}
    update_user.assert_called_once_with(3, password_hash=None, role="user", is_active=None)


def test_root_cannot_be_deleted_or_deactivated(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        route,
        "get_by_id",
        Mock(return_value={"id": 1, "username": "root", "role": "root", "is_active": 1}),
    )

    with pytest.raises(HTTPException) as exc:
        route.delete_user_route(1, _request(), _admin())

    assert exc.value.status_code == 400
