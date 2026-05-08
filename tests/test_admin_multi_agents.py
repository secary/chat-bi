"""Tests for GET/PUT /admin/multi-agents (registry YAML)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.agent.multi_agent_registry import load_registry_dict, write_registry_dict
from backend.agent.prompt_builder import scan_skills
from backend.auth_deps import require_admin
from backend.config import settings
from backend.main import app


@pytest.fixture
def admin_client(monkeypatch, tmp_path):
    """Write registry to tmp; bypass DB admin check."""

    reg_file = tmp_path / "registry.yaml"

    def _path():
        return reg_file

    monkeypatch.setattr(
        "backend.agent.multi_agent_registry._registry_path",
        _path,
    )

    def _admin():
        return {"id": 1, "username": "admin", "role": "admin"}

    app.dependency_overrides[require_admin] = _admin
    yield TestClient(app)
    app.dependency_overrides.pop(require_admin, None)


def _first_skill_slug() -> str:
    docs = scan_skills(settings.skills_dir)
    assert docs, "project must expose at least one SKILL.md"
    return docs[0].skill_dir.name


def test_get_defaults_when_missing(admin_client):
    r = admin_client.get("/admin/multi-agents")
    assert r.status_code == 200
    body = r.json()
    assert "max_agents_per_round" in body
    assert "agents" in body
    assert isinstance(body["agents"], dict)


def test_put_roundtrip(admin_client):
    slug = _first_skill_slug()
    payload = {
        "max_agents_per_round": 3,
        "agents": {
            "risk": {
                "label": "风控",
                "role_prompt": "风险视角",
                "skills": [slug],
            }
        },
    }
    r = admin_client.put("/admin/multi-agents", json=payload)
    assert r.status_code == 200
    out = r.json()
    assert out["max_agents_per_round"] == 3
    assert out["agents"]["risk"]["skills"] == [slug]

    raw = load_registry_dict()
    assert raw["max_agents_per_round"] == 3
    assert raw["agents"]["risk"]["skills"] == [slug]


def test_put_rejects_unknown_skill(admin_client):
    slug = _first_skill_slug()
    r = admin_client.put(
        "/admin/multi-agents",
        json={
            "max_agents_per_round": 2,
            "agents": {
                "a1": {
                    "label": "A",
                    "role_prompt": "",
                    "skills": [slug, "not-a-real-skill-slug-xyz"],
                }
            },
        },
    )
    assert r.status_code == 400


def test_put_rejects_invalid_agent_id(admin_client):
    slug = _first_skill_slug()
    r = admin_client.put(
        "/admin/multi-agents",
        json={
            "max_agents_per_round": 2,
            "agents": {
                "_bad": {"label": "x", "role_prompt": "", "skills": [slug]},
            },
        },
    )
    assert r.status_code == 400


def test_put_rejects_empty_agents(admin_client):
    r = admin_client.put(
        "/admin/multi-agents",
        json={"max_agents_per_round": 2, "agents": {}},
    )
    assert r.status_code == 400


def test_write_registry_dict_atomic(monkeypatch, tmp_path):
    reg_file = tmp_path / "registry.yaml"

    def _path():
        return reg_file

    monkeypatch.setattr(
        "backend.agent.multi_agent_registry._registry_path",
        _path,
    )
    write_registry_dict(
        {
            "max_agents_per_round": 2,
            "agents": {"x": {"label": "L", "role_prompt": "R", "skills": []}},
        }
    )
    assert reg_file.is_file()
    assert load_registry_dict()["agents"]["x"]["label"] == "L"
