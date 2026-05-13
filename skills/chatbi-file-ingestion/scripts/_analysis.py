from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Dict, List

SEMANTIC_SLOT_RULES: Dict[str, Dict[str, List[str]]] = {
    "status": {
        "header_aliases": ["loan_status", "贷款状态", "状态", "逾期状态", "账户状态", "五级分类"],
        "value_markers": ["逾期", "正常", "关注", "次级", "可疑", "损失"],
    },
    "overdue_days": {
        "header_aliases": ["overdue_days", "逾期天数", "逾期日数", "拖欠天数", "dpd"],
        "value_markers": [],
    },
    "principal": {
        "header_aliases": ["principal", "本金", "贷款本金", "发放本金", "授信本金"],
        "value_markers": [],
    },
    "balance": {
        "header_aliases": ["outstanding_balance", "剩余本金", "贷款余额", "余额", "未还本金"],
        "value_markers": [],
    },
    "loan_type": {
        "header_aliases": ["loan_type", "贷款类型", "业务类型", "产品类型", "授信品种"],
        "value_markers": ["房贷", "信用贷", "经营贷", "消费贷"],
    },
    "branch": {
        "header_aliases": [
            "branch_id",
            "branch_name",
            "网点编号",
            "网点",
            "支行",
            "支行名称",
            "机构",
        ],
        "value_markers": ["支行", "分行", "营业部"],
    },
}


def _decimal(value: Any) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    return Decimal(str(value))


def _safe_decimal(value: Any) -> Decimal:
    try:
        return _decimal(str(value).replace(",", ""))
    except Exception:
        return Decimal("0")


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


def _normalize_question_text(text: str) -> str:
    return "".join(ch for ch in str(text or "") if not ch.isspace()).lower()


def _normalize_name(text: str) -> str:
    return "".join(ch for ch in str(text or "") if ch not in {" ", "_", "-", "\t"}).lower()


def _find_alias_column(columns: List[str], aliases: List[str]) -> str:
    normalized_columns = {_normalize_name(column): str(column) for column in columns}
    for alias in aliases:
        matched = normalized_columns.get(_normalize_name(alias))
        if matched:
            return matched
    for alias in aliases:
        normalized_alias = _normalize_name(alias)
        for key, original in normalized_columns.items():
            if normalized_alias and normalized_alias in key:
                return original
    return ""


def _sample_column_values(dataframe: Any, column: str, limit: int = 20) -> List[str]:
    values: List[str] = []
    for raw in dataframe[column].head(limit).tolist():
        text = str(raw).strip()
        if text and text.lower() != "nan":
            values.append(text)
    return values


def infer_semantic_columns(dataframe: Any) -> Dict[str, str]:
    columns = [str(column) for column in dataframe.columns.tolist()]
    resolved: Dict[str, str] = {}
    used_columns: set[str] = set()

    for slot, rule in SEMANTIC_SLOT_RULES.items():
        header_match = _find_alias_column(columns, rule.get("header_aliases", []))
        if header_match and header_match not in used_columns:
            resolved[slot] = header_match
            used_columns.add(header_match)
            continue

        value_markers = [marker for marker in rule.get("value_markers", []) if marker]
        if not value_markers:
            continue
        best_column = ""
        best_score = 0
        for column in columns:
            if column in used_columns:
                continue
            score = 0
            for value in _sample_column_values(dataframe, column):
                score += sum(1 for marker in value_markers if marker in value)
            if score > best_score:
                best_score = score
                best_column = column
        if best_column and best_score > 0:
            resolved[slot] = best_column
            used_columns.add(best_column)

    return resolved


def _match_focus_column(question: str, columns: List[str]) -> str:
    normalized_question = _normalize_question_text(question)
    if not normalized_question:
        return ""
    for column in columns:
        if (
            _normalize_question_text(column)
            and _normalize_question_text(column) in normalized_question
        ):
            return str(column)
    return ""


def _format_pct(numerator: int, denominator: int) -> str:
    if denominator <= 0:
        return "0%"
    ratio = (Decimal(numerator) / Decimal(denominator)) * Decimal("100")
    return f"{_format_decimal(ratio)}%"


def _render_distribution_markdown(column: str, rows: List[Dict[str, Any]]) -> str:
    lines = [f"### {column}统计", "", f"| {column} | 笔数 | 占比 |", "|---|---:|---:|"]
    for row in rows:
        lines.append(f"| {row[column]} | {row['笔数']} | {row['占比']} |")
    return "\n".join(lines)


def _question_overdue_analysis(dataframe: Any, question: str) -> Dict[str, Any]:
    normalized_question = _normalize_question_text(question)
    if not normalized_question or "逾期" not in normalized_question:
        return {}

    semantic_columns = infer_semantic_columns(dataframe)
    status_col = semantic_columns.get("status", "")
    overdue_days_col = semantic_columns.get("overdue_days", "")
    principal_col = semantic_columns.get("principal", "")
    balance_col = semantic_columns.get("balance", "")
    loan_type_col = semantic_columns.get("loan_type", "")
    branch_col = semantic_columns.get("branch", "")

    overdue_mask = None
    if status_col:
        status_series = dataframe[status_col].fillna("").astype(str).map(str.strip)
        overdue_mask = status_series.str.contains("逾期", case=False, regex=False)
    if overdue_mask is None and overdue_days_col:
        overdue_days_series = dataframe[overdue_days_col].fillna(0)
        overdue_days_numeric = overdue_days_series.astype(str).str.replace(",", "", regex=False)
        overdue_days_numeric = overdue_days_numeric.map(_safe_decimal)
        overdue_mask = overdue_days_numeric > 0
    if overdue_mask is None:
        return {}

    total_count = int(len(dataframe.index))
    overdue_frame = dataframe.loc[overdue_mask].copy()
    overdue_count = int(len(overdue_frame.index))
    if overdue_count <= 0:
        return {
            "text": f"已根据您的问题检查逾期情况，共 {total_count} 行数据，当前未发现逾期记录。",
            "summary_title": "逾期贷款分析",
            "focus_column": status_col or overdue_days_col or "逾期情况",
            "distribution_rows": [],
            "overdue_summary": {
                "total_count": total_count,
                "overdue_count": 0,
                "overdue_rate": "0%",
            },
            "recommendations": ["当前未发现逾期贷款，建议继续保持贷后预警与到期提醒机制。"],
        }

    overdue_rate = _format_pct(overdue_count, total_count)
    summary = {
        "total_count": total_count,
        "overdue_count": overdue_count,
        "overdue_rate": overdue_rate,
    }

    lines = [
        "## 逾期情况统计",
        "",
        f"- 总记录数：{total_count}",
        f"- 逾期记录数：{overdue_count}",
        f"- 逾期率：{overdue_rate}",
    ]

    overdue_days_numbers: List[Decimal] = []
    if overdue_days_col:
        cleaned_days = (
            overdue_frame[overdue_days_col]
            .fillna(0)
            .astype(str)
            .str.replace(",", "", regex=False)
            .tolist()
        )
        for value in cleaned_days:
            number = _safe_decimal(value)
            overdue_days_numbers.append(number)
        if overdue_days_numbers:
            avg_days = sum(overdue_days_numbers, Decimal("0")) / Decimal(len(overdue_days_numbers))
            max_days = max(overdue_days_numbers)
            summary["avg_overdue_days"] = _format_decimal(avg_days)
            summary["max_overdue_days"] = _format_decimal(max_days)
            lines.append(f"- 平均逾期天数：{_format_decimal(avg_days)} 天")
            lines.append(f"- 最大逾期天数：{_format_decimal(max_days)} 天")

    if principal_col:
        principal_values = (
            overdue_frame[principal_col].fillna(0).astype(str).str.replace(",", "", regex=False)
        )
        total_principal = sum((_safe_decimal(value) for value in principal_values), Decimal("0"))
        summary["overdue_principal_sum"] = _format_decimal(total_principal)
        lines.append(f"- 逾期贷款本金合计：{_format_decimal(total_principal)}")

    if balance_col:
        balance_values = (
            overdue_frame[balance_col].fillna(0).astype(str).str.replace(",", "", regex=False)
        )
        total_balance = sum((_safe_decimal(value) for value in balance_values), Decimal("0"))
        summary["overdue_balance_sum"] = _format_decimal(total_balance)
        lines.append(f"- 逾期剩余本金合计：{_format_decimal(total_balance)}")

    distribution_rows: List[Dict[str, Any]] = []
    distribution_label = ""
    if loan_type_col:
        type_counts = (
            overdue_frame[loan_type_col]
            .fillna("未知")
            .astype(str)
            .map(lambda value: value.strip() or "未知")
            .value_counts(dropna=False)
        )
        distribution_rows = [
            {
                loan_type_col: str(value),
                "笔数": int(count),
                "占比": _format_pct(int(count), overdue_count),
            }
            for value, count in type_counts.head(10).items()
        ]
        distribution_label = loan_type_col
    elif branch_col:
        branch_counts = (
            overdue_frame[branch_col]
            .fillna("未知")
            .astype(str)
            .map(lambda value: value.strip() or "未知")
            .value_counts(dropna=False)
        )
        distribution_rows = [
            {
                branch_col: str(value),
                "笔数": int(count),
                "占比": _format_pct(int(count), overdue_count),
            }
            for value, count in branch_counts.head(10).items()
        ]
        distribution_label = branch_col

    if distribution_rows and distribution_label:
        top_row = distribution_rows[0]
        lines.extend(
            [
                "",
                f"### 按{distribution_label}分布",
                "",
                f"当前逾期最集中的{distribution_label}为「{top_row[distribution_label]}」，"
                f"共 {top_row['笔数']} 笔，占比 {top_row['占比']}。",
                "",
                _render_distribution_markdown(distribution_label, distribution_rows),
            ]
        )

    recommendations: List[str] = []
    overdue_rate_value = Decimal(overdue_count) / Decimal(total_count)
    if overdue_rate_value >= Decimal("0.1"):
        recommendations.append(
            "逾期率已偏高，建议按网点或客户经理维度拉出逾期清单，优先处理高余额客户。"
        )
    else:
        recommendations.append("逾期率整体可控，建议继续按周滚动监控新增逾期并跟踪回收进度。")
    if overdue_days_numbers and max(overdue_days_numbers) >= Decimal("30"):
        recommendations.append(
            "存在较长账龄逾期，建议区分 30 天内和 30 天以上客户，分层制定提醒与催收策略。"
        )
    if distribution_rows and distribution_label:
        top_row = distribution_rows[0]
        recommendations.append(
            f"可优先针对「{top_row[distribution_label]}」开展专项排查，因为该维度当前逾期占比最高。"
        )
    elif loan_type_col:
        recommendations.append(
            "建议进一步按贷款类型拆分逾期表现，识别高风险产品并收紧准入或额度策略。"
        )

    lines.extend(["", "### 建议", ""])
    for item in recommendations:
        lines.append(f"- {item}")

    return {
        "text": "\n".join(lines),
        "summary_title": "逾期贷款分析",
        "focus_column": distribution_label or status_col or overdue_days_col or "逾期情况",
        "distribution_rows": distribution_rows,
        "overdue_summary": summary,
        "recommendations": recommendations,
    }


def _question_distribution(
    dataframe: Any,
    question: str,
) -> Dict[str, Any]:
    focus_column = _match_focus_column(
        question, [str(column) for column in dataframe.columns.tolist()]
    )
    if not focus_column:
        return {}
    normalized_question = _normalize_question_text(question)
    markers = ("统计", "分布", "占比", "构成", "分析")
    if not any(marker in normalized_question for marker in markers):
        return {}

    series = (
        dataframe[focus_column]
        .fillna("空值")
        .astype(str)
        .map(lambda value: value.strip() or "空值")
    )
    counts = series.value_counts(dropna=False)
    total = int(counts.sum())
    distribution_rows = [
        {
            focus_column: str(value),
            "笔数": int(count),
            "占比": _format_pct(int(count), total),
        }
        for value, count in counts.head(20).items()
    ]
    if not distribution_rows:
        return {}

    top_row = distribution_rows[0]
    text = (
        f"已根据您的问题对字段「{focus_column}」做分布统计，共 {total} 行。"
        f"当前最多的是「{top_row[focus_column]}」，共 {top_row['笔数']} 条，占比 {top_row['占比']}。\n\n"
        f"{_render_distribution_markdown(focus_column, distribution_rows)}"
    )
    return {
        "text": text,
        "focus_column": focus_column,
        "distribution_rows": distribution_rows,
    }


def pandas_profile(
    path: Path,
    sample_size: int,
    include_rows: bool,
    question: str = "",
) -> Dict[str, Any]:
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

    question_distribution = _question_overdue_analysis(dataframe, question)
    if not question_distribution:
        question_distribution = _question_distribution(dataframe, question)

    return {
        "preview_rows": preview_rows,
        "rows": rows,
        "text": question_distribution.get("text", ""),
        "analysis": {
            "summary_title": question_distribution.get("summary_title")
            or (
                f"{question_distribution['focus_column']}分布分析"
                if question_distribution.get("focus_column")
                else "Pandas 通用表格分析"
            ),
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
            "focus_column": question_distribution.get("focus_column", ""),
            "distribution_rows": question_distribution.get("distribution_rows", []),
            "overdue_summary": question_distribution.get("overdue_summary", {}),
            "recommendations": question_distribution.get("recommendations", []),
        },
    }
