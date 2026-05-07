"""BI dashboard read-only API."""

from __future__ import annotations

from fastapi import APIRouter, Request

from backend.dashboard_overview import build_dashboard_overview
from backend.http_utils import request_trace_id
from backend.trace import log_event

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/overview")
def get_dashboard_overview(request: Request) -> dict:
    data = build_dashboard_overview()
    log_event(
        request_trace_id(request),
        "dashboard.overview",
        "viewed",
        payload={
            "warning_count": len(data.get("warnings", [])),
            "has_cards": bool(data.get("cards")),
            "has_region_sales": bool(data.get("region_sales")),
        },
    )
    return data
