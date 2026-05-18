from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str((Path(__file__).resolve().parent / "scripts").resolve()))

from _shared.runtime import ensure_active  # noqa: E402
from _shared.trace import log_skill_event  # noqa: E402
from chart_recommendation_core import recommend_from_input  # noqa: E402


@dataclass(frozen=True)
class ChartRecommendationRequest:
    raw_input: str


def run_chart_recommendation(
    request: ChartRecommendationRequest, context: Any = None
) -> dict[str, Any]:
    ensure_active(context)
    raw_input = request.raw_input.strip()
    if not raw_input:
        raise ValueError("input is required")
    log_skill_event(
        "skill.chatbi-chart-recommendation",
        "started",
        "chart recommendation started",
        {"input_preview": raw_input[:160]},
    )
    payload = recommend_from_input(raw_input)
    ensure_active(context)
    recommendation = payload.get("data", {}).get("recommendation", {})
    log_skill_event(
        "skill.chatbi-chart-recommendation",
        "completed",
        "chart recommendation completed",
        {
            "status": recommendation.get("status"),
            "recommended_chart": recommendation.get("recommended_chart"),
            "chart_count": len(payload.get("charts", []) or []),
            "kpi_count": len(payload.get("kpis", []) or []),
        },
    )
    return payload
