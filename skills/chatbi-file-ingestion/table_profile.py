from __future__ import annotations

from typing import Any, Dict, List, Sequence


def build_table_profile(headers: Sequence[str], rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    columns = []
    for header in headers:
        values = [row.get(header) for row in rows[:200]]
        non_empty = [value for value in values if value not in (None, "")]
        columns.append(
            {
                "name": str(header),
                "dtype": infer_dtype(non_empty),
                "sample_values": compact_samples(non_empty),
                "unique_count": len({str(value) for value in non_empty}),
                "null_count_sample": len(values) - len(non_empty),
            }
        )
    return {
        "row_count": len(rows),
        "column_count": len(headers),
        "columns": columns,
    }


def infer_dtype(values: Sequence[Any]) -> str:
    if not values:
        return "empty"
    numeric = sum(1 for value in values if is_number(value))
    if numeric / len(values) >= 0.8:
        return "number"
    dates = sum(1 for value in values if looks_like_date(value))
    if dates / len(values) >= 0.8:
        return "date"
    unique = len({str(value) for value in values})
    return "category" if unique <= max(20, len(values) // 3) else "text"


def is_number(value: Any) -> bool:
    try:
        float(str(value).replace(",", "").replace("%", "").strip())
        return True
    except (TypeError, ValueError):
        return False


def looks_like_date(value: Any) -> bool:
    text = str(value or "").strip().replace("/", "-")
    return len(text) >= 7 and text[4:5] == "-" and text[5:7].isdigit()


def compact_samples(values: Sequence[Any]) -> List[Any]:
    out: List[Any] = []
    for value in values:
        if value in out:
            continue
        out.append(value)
        if len(out) >= 5:
            break
    return out
