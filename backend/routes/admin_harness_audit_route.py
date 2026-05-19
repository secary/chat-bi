from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Query, Request

from backend.agent.harness_audit import build_audit_report, list_recent_audit_candidates
from backend.http_utils import request_trace_id
from backend.trace import log_event

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/harness-audits")
def admin_list_harness_audits(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
) -> Dict[str, Any]:
    rows = list_recent_audit_candidates(limit)
    log_event(
        request_trace_id(request),
        "admin.harness_audit",
        "listed",
        payload={"limit": limit, "count": len(rows)},
    )
    return {"items": rows}


@router.get("/harness-audits/{trace_id}")
def admin_get_harness_audit(trace_id: str, request: Request) -> Dict[str, Any]:
    report = build_audit_report(trace_id)
    if not report["events"]:
        raise HTTPException(status_code=404, detail="未找到对应 trace_id 的日志")
    log_event(
        request_trace_id(request),
        "admin.harness_audit",
        "inspected",
        payload={
            "target_trace_id": trace_id,
            "status": report["status"],
            "issue_count": len(report["issues"]),
        },
    )
    return report
