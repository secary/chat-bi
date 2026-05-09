from __future__ import annotations

from typing import Any, Dict, List


def build_kpi_cards(
    config: List[Dict[str, Any]],
    data: List[Dict[str, str]],
) -> List[Dict[str, Any]]:
    """Build KPI card list from config and script data."""
    cards: List[Dict[str, Any]] = []

    if not data:
        return cards

    for card_def in config:
        label = card_def.get("label", "")

        # Try to extract value from data
        value_field = card_def.get("field", label)
        value = _extract_value(data, value_field, card_def.get("default", "--"))

        cards.append(
            {
                "label": label,
                "value": value,
                "unit": card_def.get("unit", ""),
                "status": card_def.get("status", "neutral"),
            }
        )

    return cards


def _extract_value(data: List[Dict[str, str]], field: str, default: str) -> str:
    """Extract a single value from result data by field name."""
    if not data:
        return default

    # Exact match
    if field in data[0]:
        return data[0][field]

    # Try partial match
    for key in data[0]:
        if field in key or key in field:
            return data[0][key]

    return default
