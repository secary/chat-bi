from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend.auth_deps import require_admin
from backend.main import app


@pytest.fixture
def admin_client(monkeypatch, tmp_path: Path):
    skills_dir = tmp_path / "skills"
    tests_dir = tmp_path / "tests"
    skills_dir.mkdir()
    tests_dir.mkdir()

    good = skills_dir / "chatbi-demo-good"
    good.mkdir()
    (good / "SKILL.md").write_text(
        """---
name: chatbi-demo-good
description: Demo good skill
trigger_conditions:
  - 用户问 demo
required_context:
  - 需要 demo 上下文
---

## Workflow

1. do demo

## Safety

只读
""",
        encoding="utf-8",
    )
    (good / "scripts").mkdir()
    (good / "scripts" / "run_demo.py").write_text("print('ok')\n", encoding="utf-8")
    (tests_dir / "test_demo_good.py").write_text(
        "def test_demo_good():\n    assert True\n", encoding="utf-8"
    )

    weak = skills_dir / "chatbi-demo-weak"
    weak.mkdir()
    (weak / "SKILL.md").write_text(
        """---
name: chatbi-demo-weak
---

Just a note without workflow.
""",
        encoding="utf-8",
    )

    broken = skills_dir / "chatbi-demo-broken"
    broken.mkdir()

    monkeypatch.setattr(
        "backend.routes.admin_skills_route.settings",
        SimpleNamespace(skills_dir=skills_dir, project_root=tmp_path),
    )
    monkeypatch.setattr(
        "backend.routes.admin_skills_route.disabled_slugs",
        lambda: {"chatbi-demo-weak"},
    )

    def _admin():
        return {"id": 1, "username": "admin", "role": "admin"}

    app.dependency_overrides[require_admin] = _admin
    yield TestClient(app)
    app.dependency_overrides.pop(require_admin, None)


def test_admin_skill_audit_lists_status_and_issues(admin_client: TestClient):
    response = admin_client.get("/admin/skills/audit")
    assert response.status_code == 200
    body = response.json()
    assert "items" in body
    items = {item["slug"]: item for item in body["items"]}

    good = items["chatbi-demo-good"]
    assert good["status"] == "ok"
    assert good["script_count"] == 1
    assert good["test_count"] == 1
    assert good["enabled"] is True

    weak = items["chatbi-demo-weak"]
    assert weak["status"] == "warning"
    assert weak["enabled"] is False
    weak_codes = {issue["code"] for issue in weak["issues"]}
    assert "DESCRIPTION_MISSING" in weak_codes
    assert "WORKFLOW_SECTION_MISSING" in weak_codes
    assert "SCRIPT_ENTRY_MISSING" in weak_codes

    broken = items["chatbi-demo-broken"]
    assert broken["status"] == "error"
    broken_codes = {issue["code"] for issue in broken["issues"]}
    assert "SKILL_MD_MISSING" in broken_codes
