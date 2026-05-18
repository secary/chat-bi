from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _shared.runtime import ensure_active  # noqa: E402
from _shared.trace import log_skill_event  # noqa: E402
from dashboard_orchestration_core import orchestrate_from_input  # noqa: E402


@dataclass(frozen=True)
class DashboardOrchestrationRequest:
    raw_input: str


def run_dashboard_orchestration(
    request: DashboardOrchestrationRequest, context: Any = None
) -> dict[str, Any]:
    ensure_active(context)
    raw_input = request.raw_input.strip()
    if not raw_input:
        raise ValueError("input is required")
    log_skill_event(
        "skill.chatbi-dashboard-orchestration",
        "started",
        "dashboard orchestration started",
        {"input_preview": raw_input[:160]},
    )
    payload = orchestrate_from_input(raw_input)
    ensure_active(context)
    dashboard_spec = payload.get("data", {}).get("dashboard_spec", {})
    log_skill_event(
        "skill.chatbi-dashboard-orchestration",
        "completed",
        "dashboard orchestration completed",
        {
            "status": dashboard_spec.get("status"),
            "widget_count": len(dashboard_spec.get("widgets", []) or []),
            "chart_count": len(payload.get("charts", []) or []),
            "kpi_count": len(payload.get("kpis", []) or []),
        },
    )
    return payload
