from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Dict, Sequence


def normalize(value: Any) -> str:
    return str(value or "").replace("_", "").replace("-", "").replace(" ", "").lower()


def first(values: Sequence[str]) -> str:
    return str(values[0]) if values else ""


def parse_decimal(value: Any) -> Decimal | None:
    try:
        return Decimal(str(value).replace(",", "").replace("%", "").strip())
    except (InvalidOperation, AttributeError):
        return None


def month_key(value: Any) -> str:
    if isinstance(value, (date, datetime)):
        return value.strftime("%Y-%m")
    text = str(value or "").strip().replace("/", "-")
    if len(text) >= 7 and text[4:5] == "-" and text[5:7].isdigit():
        return text[:7]
    return ""


def pct(numerator: Decimal, denominator: Decimal) -> float:
    if not denominator:
        return 0.0
    value = numerator / denominator * Decimal("100")
    return float(value.quantize(Decimal("1.00"), rounding=ROUND_HALF_UP))


def stringify_rows(rows: Sequence[Dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {key: str(value) if value is not None else "" for key, value in row.items()} for row in rows
    ]
