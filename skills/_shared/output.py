from __future__ import annotations

from typing import Any, Dict, List, Optional


def skill_response(
    kind: str,
    text: str,
    data: Optional[Dict[str, Any]] = None,
    charts: Optional[List[Dict[str, Any]]] = None,
    kpis: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    return {
        "kind": kind,
        "text": text,
        "data": data or {},
        "charts": charts or [],
        "kpis": kpis or [],
    }


def kpi(label: str, value: str, unit: str = "", status: str = "neutral") -> Dict[str, str]:
    return {"label": label, "value": value, "unit": unit, "status": status}
