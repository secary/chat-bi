from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str((Path(__file__).resolve().parent / "scripts").resolve()))

from _shared.runtime import ensure_active  # noqa: E402
from _shared.trace import log_skill_event  # noqa: E402
from auto_analysis_core import analyze_from_input  # noqa: E402


@dataclass(frozen=True)
class AutoAnalysisRequest:
    raw_input: str


def run_auto_analysis(request: AutoAnalysisRequest, context: Any = None) -> dict[str, Any]:
    ensure_active(context)
    raw_input = request.raw_input.strip()
    if not raw_input:
        raise ValueError("input is required")
    log_skill_event(
        "skill.chatbi-auto-analysis",
        "started",
        "auto analysis started",
        {"input_preview": raw_input[:160]},
    )
    payload = analyze_from_input(raw_input)
    ensure_active(context)
    log_skill_event(
        "skill.chatbi-auto-analysis",
        "completed",
        "auto analysis completed",
        {
            "status": payload.get("data", {}).get("status"),
            "chart_count": len(payload.get("charts", []) or []),
            "kpi_count": len(payload.get("kpis", []) or []),
        },
    )
    return payload
