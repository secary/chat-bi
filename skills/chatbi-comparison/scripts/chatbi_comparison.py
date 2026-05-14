#!/usr/bin/env python3
"""
ChatBI comparison script.

Supports three modes:
- month_pair  : compare two specific months (default, e.g. 3月 vs 4月)
- all_months  : show all months with consecutive MoM changes (全量/全年/按月)
- quarterly   : group by quarter with QoQ changes (季度/按季)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from _shared.db import MysqlCli, default_db
from _shared.output import kpi, skill_response

DEFAULT_DB = default_db()

# ---------------------------------------------------------------------------
# Metric definitions
# ---------------------------------------------------------------------------

METRICS: Dict[str, Dict[str, Any]] = {
    "销售额": {
        "aliases": ["销售额", "收入", "成交额", "营收", "销售收入"],
        "num_col": "sales_amount",
        "den_col": None,
        "unit": "元",
        "fmt": ".0f",
    },
    "毛利": {
        "aliases": ["毛利", "毛利额", "利润"],
        "num_col": "gross_profit",
        "den_col": None,
        "unit": "元",
        "fmt": ".0f",
    },
    "毛利率": {
        "aliases": ["毛利率", "利润率"],
        "num_col": "gross_profit",
        "den_col": "sales_amount",
        "unit": "%",
        "fmt": ".2f",
    },
    "订单数": {
        "aliases": ["订单数", "订单量", "成交单数"],
        "num_col": "order_count",
        "den_col": None,
        "unit": "单",
        "fmt": ".0f",
    },
    "客户数": {
        "aliases": ["客户数", "客户量"],
        "num_col": "customer_count",
        "den_col": None,
        "unit": "人",
        "fmt": ".0f",
    },
    "目标完成率": {
        "aliases": ["目标完成率", "完成率", "达成率"],
        "num_col": "sales_amount",
        "den_col": "target_amount",
        "unit": "%",
        "fmt": ".2f",
    },
}

DIMENSIONS: Dict[str, Dict[str, str]] = {
    "区域": {"aliases": "区域,各区域,大区,地区,片区", "field": "region"},
    "渠道": {"aliases": "渠道,销售渠道,获客渠道,成交渠道", "field": "channel"},
    "产品类别": {"aliases": "产品类别,产品线,品类,产品分类,产品类型", "field": "product_category"},
    "客户类型": {"aliases": "客户类型,客群,客户类别,客户分层", "field": "customer_type"},
    "部门": {"aliases": "部门,团队,事业部", "field": "department"},
}

QUARTER_MAP = {
    1: "Q1",
    2: "Q1",
    3: "Q1",
    4: "Q2",
    5: "Q2",
    6: "Q2",
    7: "Q3",
    8: "Q3",
    9: "Q3",
    10: "Q4",
    11: "Q4",
    12: "Q4",
}

# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def _q(text: str) -> str:
    return re.sub(r"\s+", "", text).lower()


def _normalize_month_placeholders(q: str) -> str:
    """「1月份」与「1月」等价，便于月份正则匹配（不影响「三个月」等非数字+月份结构）。"""
    return re.sub(r"(\d{1,2})月份", r"\1月", q)


def detect_metric(question: str) -> Tuple[str, Dict]:
    q = _q(question)
    for name, meta in METRICS.items():
        if any(alias in q for alias in meta["aliases"]):
            return name, meta
    return "销售额", METRICS["销售额"]


def detect_dimension(question: str) -> Tuple[str, str]:
    q = _q(question)
    for name, meta in DIMENSIONS.items():
        if any(alias in q for alias in meta["aliases"].split(",")):
            return name, meta["field"]
    return "区域", "region"


def detect_mode(question: str) -> str:
    """Return 'all_months', 'quarterly', or 'month_pair'."""
    q = _q(question)
    if any(kw in q for kw in ["全量", "全年", "所有月", "每月", "各月", "月度趋势", "全部月"]):
        return "all_months"
    if any(
        kw in q
        for kw in [
            "季度",
            "按季",
            "季环比",
            "q1",
            "q2",
            "q3",
            "q4",
            "第一季",
            "第二季",
            "第三季",
            "第四季",
        ]
    ):
        return "quarterly"
    return "month_pair"


def detect_months(question: str, db: MysqlCli) -> Tuple[int, int, int]:
    """Return (year, current_month, prev_month) for month_pair mode."""
    q = _normalize_month_placeholders(_q(question))
    pair = re.search(r"(\d{1,2})月[和与对比vsvs]+(\d{1,2})月", q)
    if pair:
        m1, m2 = int(pair.group(1)), int(pair.group(2))
        return 2026, max(m1, m2), min(m1, m2)
    single = re.search(r"(\d{1,2})月", q)
    if single:
        cur = int(single.group(1))
        return 2026, cur, (cur - 1) if cur > 1 else 12
    rows = db.query(
        "SELECT MAX(MONTH(order_date)) AS m FROM sales_order WHERE YEAR(order_date)=2026"
    )
    cur = int(rows[0]["m"]) if rows else 4
    return 2026, cur, (cur - 1) if cur > 1 else 12


def detect_year(question: str) -> int:
    m = re.search(r"(202\d)年", question)
    return int(m.group(1)) if m else 2026


# ---------------------------------------------------------------------------
# SQL helpers
# ---------------------------------------------------------------------------


def _month_expr(col: str, month: int) -> str:
    return f"SUM(CASE WHEN MONTH(order_date)={month} THEN `{col}` ELSE 0 END)"


def _metric_expr_for_month(meta: Dict, month: int) -> str:
    num, den = meta["num_col"], meta["den_col"]
    if den:
        return f"{_month_expr(num, month)} / NULLIF({_month_expr(den, month)}, 0) * 100"
    return _month_expr(num, month)


def _metric_expr_simple(meta: Dict) -> str:
    num, den = meta["num_col"], meta["den_col"]
    if den:
        return f"SUM(`{num}`) / NULLIF(SUM(`{den}`), 0) * 100"
    return f"SUM(`{num}`)"


# ---------------------------------------------------------------------------
# Mode: month_pair
# ---------------------------------------------------------------------------


def run_month_pair(
    db: MysqlCli,
    meta: Dict,
    dim_field: str,
    dim_name: str,
    metric_name: str,
    year: int,
    cur: int,
    prev: int,
) -> Dict[str, Any]:
    cur_label = f"{cur}月{metric_name}"
    prev_label = f"{prev}月{metric_name}"

    sql = (
        f"SELECT `{dim_field}` AS dimension, "
        f"({_metric_expr_for_month(meta, cur)}) AS cur_val, "
        f"({_metric_expr_for_month(meta, prev)}) AS prev_val "
        f"FROM sales_order "
        f"WHERE YEAR(order_date)={year} AND MONTH(order_date) IN ({cur},{prev}) "
        f"GROUP BY `{dim_field}` ORDER BY cur_val DESC"
    )
    rows = db.query(sql)
    if not rows:
        return skill_response("text", "未查询到数据。")

    raw_rows = [
        {
            "dimension": r["dimension"],
            cur_label: round(float(r["cur_val"] or 0), 2),
            prev_label: round(float(r["prev_val"] or 0), 2),
        }
        for r in rows
    ]

    chart_plan = {
        "chart_type": "bar",
        "title": f"{cur}月 vs {prev}月 {metric_name}环比（按{dim_name}）",
        "dimension": "dimension",
        "metrics": [cur_label, prev_label],
        "highlight": {"mode": "max", "field": cur_label},
    }

    top = rows[0]
    cv0, pv0 = float(top["cur_val"] or 0), float(top["prev_val"] or 0)
    rate0 = ((cv0 - pv0) / pv0 * 100) if pv0 else None
    rate_str = f"{rate0:+.1f}%" if rate0 is not None else "无基准"
    text = (
        f"{year}年{cur}月 vs {prev}月 · **{metric_name}环比**（按{dim_name}）\n\n"
        f"**{top['dimension']}** 环比{rate_str}，"
        f"{_fmt(pv0, meta)} → {_fmt(cv0, meta)}。\n\n" + _md_table_pair(rows, meta, cur, prev)
    )

    cur_total = sum(float(r["cur_val"] or 0) for r in rows)
    prev_total = sum(float(r["prev_val"] or 0) for r in rows)
    kpis = _pair_kpis(cur_total, prev_total, meta, cur, prev)

    return {
        "kind": "table",
        "text": text,
        "chart_plan": chart_plan,
        "data": {"rows": raw_rows},
        "charts": [],
        "kpis": kpis,
    }


# ---------------------------------------------------------------------------
# Mode: all_months
# ---------------------------------------------------------------------------


def run_all_months(
    db: MysqlCli,
    meta: Dict,
    metric_name: str,
    year: int,
) -> Dict[str, Any]:
    sql = (
        f"SELECT MONTH(order_date) AS month, "
        f"({_metric_expr_simple(meta)}) AS val "
        f"FROM sales_order WHERE YEAR(order_date)={year} "
        f"GROUP BY MONTH(order_date) ORDER BY month"
    )
    rows = db.query(sql)
    if not rows:
        return skill_response("text", "未查询到数据。")

    month_vals = [(int(r["month"]), float(r["val"] or 0)) for r in rows]

    # Build raw rows for chart: month label + value + MoM change
    raw_rows = []
    md_lines = [
        f"| 月份 | {metric_name} | 环比变化 | 环比增长率 |",
        "|------|------|--------|------|",
    ]
    for i, (m, v) in enumerate(month_vals):
        prev_v = month_vals[i - 1][1] if i > 0 else None
        change = v - prev_v if prev_v is not None else 0.0
        rate = (change / prev_v * 100) if prev_v else None
        rate_str = f"{rate:+.1f}%" if rate is not None else "—"
        raw_rows.append({"月份": f"{m}月", metric_name: round(v, 2)})
        md_lines.append(f"| {m}月 | {_fmt(v, meta)} | {_fmt_change(change, meta)} | {rate_str} |")

    chart_plan = {
        "chart_type": "line",
        "title": f"{year}年{metric_name}月度走势",
        "dimension": "月份",
        "metrics": [metric_name],
    }

    text = f"{year}年 · **{metric_name}月度走势与环比**\n\n" + "\n".join(md_lines)

    total = sum(v for _, v in month_vals)
    kpis = [
        kpi(f"{year}年累计{metric_name}", _fmt(total, meta)),
        kpi("月均", _fmt(total / len(month_vals), meta)),
        kpi("数据月份数", f"{len(month_vals)}个月"),
    ]

    return {
        "kind": "table",
        "text": text,
        "chart_plan": chart_plan,
        "data": {"rows": raw_rows},
        "charts": [],
        "kpis": kpis,
    }


# ---------------------------------------------------------------------------
# Mode: quarterly
# ---------------------------------------------------------------------------


def run_quarterly(
    db: MysqlCli,
    meta: Dict,
    metric_name: str,
    year: int,
) -> Dict[str, Any]:
    sql = (
        f"SELECT MONTH(order_date) AS month, "
        f"({_metric_expr_simple(meta)}) AS val "
        f"FROM sales_order WHERE YEAR(order_date)={year} "
        f"GROUP BY MONTH(order_date)"
    )
    rows = db.query(sql)
    if not rows:
        return skill_response("text", "未查询到数据。")

    # Aggregate by quarter
    q_data: Dict[str, List[float]] = {}
    for r in rows:
        m, v = int(r["month"]), float(r["val"] or 0)
        q = QUARTER_MAP[m]
        q_data.setdefault(q, []).append(v)

    quarters = sorted(q_data.keys())
    # For ratio metrics, average; for sum metrics, sum
    is_ratio = meta["den_col"] is not None
    q_vals = [
        (q, (sum(q_data[q]) / len(q_data[q])) if is_ratio else sum(q_data[q])) for q in quarters
    ]

    raw_rows = [{"季度": q, metric_name: round(v, 2)} for q, v in q_vals]

    md_lines = [
        f"| 季度 | {metric_name} | 环比变化 | 环比增长率 |",
        "|------|------|--------|------|",
    ]
    for i, (q, v) in enumerate(q_vals):
        prev_v = q_vals[i - 1][1] if i > 0 else None
        change = v - prev_v if prev_v is not None else 0.0
        rate = (change / prev_v * 100) if prev_v else None
        rate_str = f"{rate:+.1f}%" if rate is not None else "—"
        md_lines.append(f"| {q} | {_fmt(v, meta)} | {_fmt_change(change, meta)} | {rate_str} |")

    chart_plan = {
        "chart_type": "bar",
        "title": f"{year}年{metric_name}季度环比",
        "dimension": "季度",
        "metrics": [metric_name],
    }

    text = f"{year}年 · **{metric_name}季度环比**\n\n" + "\n".join(md_lines)

    total = sum(v for _, v in q_vals)
    kpis = [
        kpi(f"{year}年累计{metric_name}", _fmt(total, meta)),
        kpi("季度数", f"{len(q_vals)}个季度"),
    ]

    return {
        "kind": "table",
        "text": text,
        "chart_plan": chart_plan,
        "data": {"rows": raw_rows},
        "charts": [],
        "kpis": kpis,
    }


# ---------------------------------------------------------------------------
# Shared formatters
# ---------------------------------------------------------------------------


def _fmt(val: float, meta: Dict) -> str:
    unit, fmt = meta["unit"], meta["fmt"]
    if unit == "%":
        return f"{val:{fmt}}%"
    if unit == "元" and abs(val) >= 10000:
        return f"{val / 10000:.1f}万元"
    return f"{val:{fmt}}{unit}"


def _fmt_change(change: float, meta: Dict) -> str:
    sign = "+" if change >= 0 else ""
    unit = meta["unit"]
    if unit == "元" and abs(change) >= 10000:
        return f"{sign}{change / 10000:.1f}万元"
    if unit == "%":
        return f"{sign}{change:.2f}pct"
    return f"{sign}{change:.1f}"


def _md_table_pair(rows: List[Dict], meta: Dict, cur: int, prev: int) -> str:
    lines = [
        f"| 维度 | {cur}月 | {prev}月 | 环比变化 | 增长率 |",
        "|------|------|------|--------|------|",
    ]
    for r in rows:
        cv, pv = float(r["cur_val"] or 0), float(r["prev_val"] or 0)
        change = cv - pv
        rate = (change / pv * 100) if pv else None
        rate_str = f"{rate:+.1f}%" if rate is not None else "—"
        lines.append(
            f"| {r['dimension']} | {_fmt(cv, meta)} | {_fmt(pv, meta)} "
            f"| {_fmt_change(change, meta)} | {rate_str} |"
        )
    return "\n".join(lines)


def _pair_kpis(cur_total: float, prev_total: float, meta: Dict, cur: int, prev: int) -> List:
    change = cur_total - prev_total
    rate = (change / prev_total * 100) if prev_total else None
    return [
        kpi(f"{cur}月{meta['unit'] and '合计' or ''}", _fmt(cur_total, meta)),
        kpi(f"{prev}月", _fmt(prev_total, meta)),
        kpi(
            "环比变化", _fmt_change(change, meta), status="positive" if change >= 0 else "negative"
        ),
        kpi(
            "环比增长率",
            f"{rate:+.1f}%" if rate is not None else "—",
            status="positive" if (rate or 0) >= 0 else "negative",
        ),
    ]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("question")
    parser.add_argument("--json", action="store_true", dest="json_out")
    args = parser.parse_args()

    db = MysqlCli(DEFAULT_DB)
    question = args.question

    metric_name, metric_meta = detect_metric(question)
    dim_name, dim_field = detect_dimension(question)
    mode = detect_mode(question)
    year = detect_year(question)

    try:
        if mode == "all_months":
            out = run_all_months(db, metric_meta, metric_name, year)
        elif mode == "quarterly":
            out = run_quarterly(db, metric_meta, metric_name, year)
        else:
            _, cur_month, prev_month = detect_months(question, db)
            out = run_month_pair(
                db, metric_meta, dim_field, dim_name, metric_name, year, cur_month, prev_month
            )
    except RuntimeError as exc:
        out = skill_response("error", f"查询失败：{exc}")

    print(json.dumps(out, ensure_ascii=False, indent=2 if args.json_out else None))


if __name__ == "__main__":
    main()
