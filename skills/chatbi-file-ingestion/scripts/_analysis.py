from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Dict, List


def _decimal(value: Any) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    return Decimal(str(value))


def _format_decimal(value: Decimal, digits: int = 2) -> str:
    quant = Decimal("1") if digits == 0 else Decimal(f"1.{'0' * digits}")
    normalized = value.quantize(quant, rounding=ROUND_HALF_UP)
    text = format(normalized, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def _month_key(value: Any) -> str:
    if isinstance(value, (date, datetime)):
        return value.strftime("%Y-%m")
    return str(value)[:7]


def analyze_known_table(table: str, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    if table == "sales_order":
        return analyze_sales_order(rows)
    if table == "customer_profile":
        return analyze_customer_profile(rows)
    return {"summary_title": "业务表分析", "key_metrics": [], "highlights": [], "trend": []}


def analyze_sales_order(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    total_sales = Decimal("0")
    total_profit = Decimal("0")
    total_target = Decimal("0")
    region_sales: Dict[str, Decimal] = defaultdict(Decimal)
    product_sales: Dict[str, Decimal] = defaultdict(Decimal)
    month_sales: Dict[str, Decimal] = defaultdict(Decimal)

    for row in rows:
        sales = _decimal(row.get("sales_amount"))
        profit = _decimal(row.get("gross_profit"))
        target = _decimal(row.get("target_amount"))
        total_sales += sales
        total_profit += profit
        total_target += target
        region_sales[str(row.get("region") or "未知区域")] += sales
        product_sales[str(row.get("product_name") or "未知产品")] += sales
        month_sales[_month_key(row.get("order_date") or "")] += sales

    margin_pct = (total_profit / total_sales) * Decimal("100") if total_sales else Decimal("0")
    achieve_pct = (total_sales / total_target) * Decimal("100") if total_target else Decimal("0")
    top_region = max(region_sales.items(), key=lambda item: item[1], default=None)
    top_product = max(product_sales.items(), key=lambda item: item[1], default=None)

    highlights = []
    if top_region:
        highlights.append(
            f"销售额最高区域为{top_region[0]}，共{_format_decimal(top_region[1])}元。"
        )
    if top_product:
        highlights.append(
            f"销售额最高产品为{top_product[0]}，共{_format_decimal(top_product[1])}元。"
        )
    if total_target:
        highlights.append(f"整体目标完成率为{_format_decimal(achieve_pct)}%。")

    trend = [
        {"month": month, "sales_amount": _format_decimal(amount)}
        for month, amount in sorted(month_sales.items())
    ]
    return {
        "summary_title": "销售订单业务分析",
        "key_metrics": [
            {"label": "总销售额", "value": _format_decimal(total_sales), "unit": "元"},
            {"label": "总毛利", "value": _format_decimal(total_profit), "unit": "元"},
            {"label": "毛利率", "value": _format_decimal(margin_pct), "unit": "%"},
            {"label": "目标完成率", "value": _format_decimal(achieve_pct), "unit": "%"},
        ],
        "highlights": highlights,
        "trend": trend,
    }


def analyze_customer_profile(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    total_new = 0
    total_active = 0
    total_retained = 0
    total_churned = 0
    region_active: Dict[str, int] = defaultdict(int)
    month_active: Dict[str, int] = defaultdict(int)

    for row in rows:
        new_customers = int(row.get("new_customers") or 0)
        active_customers = int(row.get("active_customers") or 0)
        retained_customers = int(row.get("retained_customers") or 0)
        churned_customers = int(row.get("churned_customers") or 0)
        total_new += new_customers
        total_active += active_customers
        total_retained += retained_customers
        total_churned += churned_customers
        region_active[str(row.get("region") or "未知区域")] += active_customers
        month_active[_month_key(row.get("stat_month") or "")] += active_customers

    denominator = total_retained + total_churned
    retention_pct = (
        (Decimal(total_retained) / Decimal(denominator) * Decimal("100"))
        if denominator
        else Decimal("0")
    )
    top_region = max(region_active.items(), key=lambda item: item[1], default=None)

    highlights = []
    if top_region:
        highlights.append(f"活跃客户最多区域为{top_region[0]}，共{top_region[1]}人。")
    if denominator:
        highlights.append(f"按留存/流失口径汇总，整体留存率为{_format_decimal(retention_pct)}%。")

    trend = [
        {"month": month, "active_customers": active}
        for month, active in sorted(month_active.items())
    ]
    return {
        "summary_title": "客户画像业务分析",
        "key_metrics": [
            {"label": "新增客户数", "value": str(total_new), "unit": "人"},
            {"label": "活跃客户数", "value": str(total_active), "unit": "人"},
            {"label": "留存客户数", "value": str(total_retained), "unit": "人"},
            {"label": "留存率", "value": _format_decimal(retention_pct), "unit": "%"},
        ],
        "highlights": highlights,
        "trend": trend,
    }


def _sanitize_value(value: Any) -> Any:
    if value is None:
        return None
    try:
        import pandas as pd

        if pd.isna(value):
            return None
    except Exception:
        pass
    if hasattr(value, "item"):
        try:
            value = value.item()
        except Exception:
            pass
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def pandas_profile(path: Path, sample_size: int, include_rows: bool) -> Dict[str, Any]:
    try:
        import pandas as pd
    except ImportError as exc:
        raise RuntimeError("通用文件分析需要安装 pandas") from exc

    if path.suffix.lower() == ".csv":
        dataframe = pd.read_csv(path)
    else:
        dataframe = pd.read_excel(path)

    preview_rows = [
        {str(key): _sanitize_value(value) for key, value in row.items()}
        for row in dataframe.head(sample_size).to_dict(orient="records")
    ]
    rows = []
    if include_rows:
        rows = [
            {str(key): _sanitize_value(value) for key, value in row.items()}
            for row in dataframe.to_dict(orient="records")
        ]

    numeric_summary = []
    numeric_df = dataframe.select_dtypes(include="number")
    for column in list(numeric_df.columns)[:8]:
        series = numeric_df[column].dropna()
        if series.empty:
            continue
        numeric_summary.append(
            {
                "column": str(column),
                "sum": _sanitize_value(series.sum()),
                "mean": _sanitize_value(series.mean()),
                "min": _sanitize_value(series.min()),
                "max": _sanitize_value(series.max()),
            }
        )

    categorical_summary = []
    object_columns = [
        column
        for column in dataframe.columns
        if str(dataframe[column].dtype) in {"object", "string", "category"}
    ]
    for column in object_columns[:5]:
        values = [
            str(value).strip()
            for value in dataframe[column].tolist()
            if value is not None and str(value).strip()
        ]
        if not values:
            continue
        top_values = [
            {"value": value, "count": count} for value, count in Counter(values).most_common(5)
        ]
        categorical_summary.append({"column": str(column), "top_values": top_values})

    return {
        "preview_rows": preview_rows,
        "rows": rows,
        "analysis": {
            "summary_title": "Pandas 通用表格分析",
            "shape": {"rows": int(len(dataframe.index)), "columns": int(len(dataframe.columns))},
            "columns": [str(column) for column in dataframe.columns.tolist()],
            "dtypes": {str(key): str(value) for key, value in dataframe.dtypes.astype(str).items()},
            "null_counts": {
                str(key): int(value)
                for key, value in dataframe.isna().sum().items()
                if int(value) > 0
            },
            "numeric_summary": numeric_summary,
            "categorical_summary": categorical_summary,
        },
    }
