from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any, Dict, List, Sequence, Tuple

from utils import month_key, parse_decimal


def validate_metric_plans(
    plans: Sequence[Dict[str, Any]], profile: Dict[str, Any]
) -> List[Dict[str, Any]]:
    available = {str(column["name"]) for column in profile["columns"]}
    valid = []
    for plan in plans:
        formula = plan.get("formula")
        group_by = plan.get("group_by") or []
        if not isinstance(formula, dict) or not isinstance(group_by, list):
            continue
        referenced = formula_fields(formula) | group_fields(group_by)
        if referenced - available:
            continue
        valid.append(
            {
                "id": str(plan.get("id") or f"metric_{len(valid) + 1}"),
                "name": str(plan.get("name") or "自动指标"),
                "description": str(plan.get("description") or "由表结构和用户问题自动建议。"),
                "formula_md": str(plan.get("formula_md") or "`formula`"),
                "formula": formula,
                "group_by": group_by,
                "matched_fields": sorted(referenced),
                "chart_hint": str(plan.get("chart_hint") or "bar"),
                "confidence": float(plan.get("confidence") or 0.7),
                "selected": bool(plan.get("selected", True)),
            }
        )
    return valid[:5]


def derive_metric(metric_plan: Dict[str, Any], rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    grouped = group_rows(rows, metric_plan.get("group_by") or [])
    metric_name = str(metric_plan.get("name") or "指标值")
    derived = []
    for key, group in sorted(grouped.items(), key=lambda item: item[0]):
        row = dict(key)
        row[metric_name] = float(eval_formula(metric_plan["formula"], group))
        derived.append(row)
    return {**metric_plan, "rows": derived}


def group_rows(
    rows: Sequence[Dict[str, Any]], group_by: Sequence[Dict[str, str]]
) -> Dict[Tuple[Tuple[str, str], ...], List[Dict[str, Any]]]:
    if not group_by:
        return {(("范围", "整体"),): list(rows)}
    grouped: Dict[Tuple[Tuple[str, str], ...], List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        parts = []
        for spec in group_by:
            field = str(spec.get("field") or "")
            alias = str(spec.get("alias") or field)
            value = row.get(field)
            if spec.get("transform") == "month":
                value = month_key(value)
            parts.append((alias, str(value or "未分类")))
        grouped[tuple(parts)].append(row)
    return grouped


def eval_formula(formula: Dict[str, Any], rows: Sequence[Dict[str, Any]]) -> Decimal:
    op = str(formula.get("op") or "").lower()
    if op == "sum":
        return sum_values(rows, str(formula.get("field") or ""), formula.get("filter"))
    if op == "count":
        return Decimal(len(apply_filter(rows, formula.get("filter"))))
    if op == "count_distinct":
        filtered = apply_filter(rows, formula.get("filter"))
        field = str(formula.get("field") or "")
        return Decimal(len({str(row.get(field) or "") for row in filtered}))
    if op == "subtract":
        return eval_formula(formula.get("left") or {}, rows) - eval_formula(
            formula.get("right") or {}, rows
        )
    if op in {"divide", "ratio", "ratio_percent"}:
        denominator = eval_formula(formula.get("denominator") or {}, rows)
        if not denominator:
            return Decimal("0")
        value = eval_formula(formula.get("numerator") or {}, rows) / denominator
        return value * Decimal("100") if op == "ratio_percent" else value
    return Decimal("0")


def sum_values(rows: Sequence[Dict[str, Any]], field: str, filter_spec: Any = None) -> Decimal:
    total = Decimal("0")
    for row in apply_filter(rows, filter_spec):
        total += parse_decimal(row.get(field)) or Decimal("0")
    return total


def apply_filter(rows: Sequence[Dict[str, Any]], filter_spec: Any = None) -> List[Dict[str, Any]]:
    if not filter_spec:
        return list(rows)
    return [row for row in rows if match_filter(row, filter_spec)]


def match_filter(row: Dict[str, Any], spec: Any) -> bool:
    if not isinstance(spec, dict):
        return True
    if "any" in spec:
        return any(match_filter(row, item) for item in spec.get("any") or [])
    if "all" in spec:
        return all(match_filter(row, item) for item in spec.get("all") or [])
    field = str(spec.get("field") or "")
    op = str(spec.get("op") or "eq")
    expected = spec.get("value")
    actual = row.get(field)
    if op == "contains":
        return str(expected) in str(actual or "")
    if op == "eq":
        return str(actual) == str(expected)
    actual_number = parse_decimal(actual) or Decimal("0")
    expected_number = parse_decimal(expected) or Decimal("0")
    if op == "gt":
        return actual_number > expected_number
    if op == "gte":
        return actual_number >= expected_number
    if op == "lt":
        return actual_number < expected_number
    if op == "lte":
        return actual_number <= expected_number
    return False


def formula_fields(formula: Any) -> set[str]:
    if not isinstance(formula, dict):
        return set()
    fields = {str(formula["field"])} if formula.get("field") else set()
    for key in ("left", "right", "numerator", "denominator"):
        fields |= formula_fields(formula.get(key))
    fields |= filter_fields(formula.get("filter"))
    return fields


def filter_fields(spec: Any) -> set[str]:
    if not isinstance(spec, dict):
        return set()
    fields = {str(spec["field"])} if spec.get("field") else set()
    for key in ("any", "all"):
        for item in spec.get(key) or []:
            fields |= filter_fields(item)
    return fields


def group_fields(group_by: Sequence[Dict[str, str]]) -> set[str]:
    return {str(item.get("field")) for item in group_by if item.get("field")}
