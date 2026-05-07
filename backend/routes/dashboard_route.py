"""BI dashboard read-only API."""

from __future__ import annotations

from fastapi import APIRouter

from backend.dashboard_overview import build_dashboard_overview

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/overview")
def get_dashboard_overview() -> dict:
    return build_dashboard_overview()
