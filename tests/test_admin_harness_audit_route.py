from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.auth_deps import require_admin
from backend.main import app


@pytest.fixture
def admin_client():
    def _admin():
        return {"id": 1, "username": "admin", "role": "admin"}

    app.dependency_overrides[require_admin] = _admin
    yield TestClient(app)
    app.dependency_overrides.pop(require_admin, None)


def test_get_harness_audit(monkeypatch, admin_client):
    monkeypatch.setattr(
        "backend.routes.admin_harness_audit_route.build_audit_report",
        lambda trace_id: {
            "trace_id": trace_id,
            "status": "warning",
            "score": 88,
            "summary": "链路可完成，但存在可疑波动或约束回退。",
            "issues": [{"code": "HARNESS_POLICY_REJECTED", "level": "warning", "message": "x"}],
            "business_flows": [],
            "events": [{"id": 1}],
            "event_count": 1,
        },
    )
    response = admin_client.get("/admin/harness-audits/trace123")
    assert response.status_code == 200
    body = response.json()
    assert body["trace_id"] == "trace123"
    assert body["status"] == "warning"


def test_get_harness_audit_404_when_missing(monkeypatch, admin_client):
    monkeypatch.setattr(
        "backend.routes.admin_harness_audit_route.build_audit_report",
        lambda trace_id: {
            "trace_id": trace_id,
            "status": "ok",
            "score": 100,
            "summary": "未发现明显异常。",
            "issues": [],
            "business_flows": [],
            "events": [],
            "event_count": 0,
        },
    )
    response = admin_client.get("/admin/harness-audits/missing")
    assert response.status_code == 404
