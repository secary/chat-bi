from __future__ import annotations

from typing import Any, Dict, List, Sequence

from utils import month_key, normalize, parse_decimal


def build_profile(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    keys = list(rows[0].keys()) if rows else []
    columns = []
    for key in keys:
        values = [row.get(key) for row in rows[:200]]
        columns.append(
            {
                "name": key,
                "dtype": infer_dtype(values),
                "semantic_role": infer_role(key, values),
                "sample_values": compact_samples(values),
                "unique_count": len({str(v) for v in values if v not in (None, "")}),
            }
        )
    return {
        "row_count": len(rows),
        "columns": columns,
        "time_columns": names_by_role(columns, "time"),
        "id_columns": names_by_role(columns, "id"),
        "numeric_columns": [c["name"] for c in columns if c["dtype"] == "number"],
        "categorical_columns": [c["name"] for c in columns if c["dtype"] == "category"],
        "domain_guess": infer_domain(columns),
    }


def infer_dtype(values: Sequence[Any]) -> str:
    non_empty = [v for v in values if v not in (None, "")]
    if not non_empty:
        return "empty"
    numeric = sum(1 for value in non_empty if parse_decimal(value) is not None)
    if numeric / len(non_empty) >= 0.8:
        return "number"
    dates = sum(1 for value in non_empty if month_key(value))
    if dates / len(non_empty) >= 0.8:
        return "date"
    unique = len({str(v) for v in non_empty})
    return "category" if unique <= max(20, len(non_empty) // 3) else "text"


def infer_role(name: str, values: Sequence[Any]) -> str:
    normalized = normalize(name)
    if any(token in normalized for token in ["date", "month", "time", "日期", "月份", "时间"]):
        return "time"
    if "id" in normalized or any(token in normalized for token in ["编号", "客户号"]):
        return "id"
    if any(token in normalized for token in ["status", "状态", "逾期", "分类"]):
        return "status"
    if any(token in normalized for token in ["cost", "成本", "费用", "投入", "spend"]):
        return "cost"
    if any(token in normalized for token in ["revenue", "收入", "营收", "sales", "销售额"]):
        return "revenue"
    if any(token in normalized for token in ["profit", "毛利", "利润", "收益"]):
        return "profit"
    if any(token in normalized for token in ["principal", "本金", "余额", "amount", "金额"]):
        return "amount"
    if any(token in normalized for token in ["retained", "留存"]):
        return "retained"
    if any(token in normalized for token in ["churn", "流失"]):
        return "churned"
    if any(token in normalized for token in ["active", "活跃"]):
        return "active"
    dtype = infer_dtype(values)
    return "measure" if dtype == "number" else dtype


def compact_samples(values: Sequence[Any]) -> List[Any]:
    out = []
    for value in values:
        if value in (None, "") or value in out:
            continue
        out.append(value)
        if len(out) >= 5:
            break
    return out


def names_by_role(columns: Sequence[Dict[str, Any]], role: str) -> List[str]:
    return [str(c["name"]) for c in columns if c["semantic_role"] == role or c["dtype"] == role]


def infer_domain(columns: Sequence[Dict[str, Any]]) -> str:
    joined = " ".join(normalize(c["name"]) for c in columns)
    if any(token in joined for token in ["loan", "贷款", "本金", "逾期"]):
        return "loan_risk"
    if any(token in joined for token in ["customer", "客户", "留存", "流失"]):
        return "customer"
    if any(token in joined for token in ["roi", "cost", "成本", "收入", "投放"]):
        return "marketing_roi"
    return "generic_table"
