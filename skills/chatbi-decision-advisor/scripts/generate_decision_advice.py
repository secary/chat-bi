#!/usr/bin/env python3
"""
Generate rule-based ChatBI decision advice from demo MySQL metrics.

The script computes governed facts first, then derives recommendations from
explicit rules. It does not ask a model to invent conclusions from raw tables.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, asdict
from decimal import Decimal
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from _shared.db import MysqlCli, default_db, quote_ident, quote_literal
from _shared.output import kpi, skill_response

DEFAULT_DB = default_db()


@dataclass
class Advice:
    priority: str
    theme: str
    decision: str
    reason: str
    actions: List[str]


@dataclass
class Scope:
    question: str
    sales_conditions: List[str]
    customer_conditions: List[str]
    labels: List[str]
    has_sales_only_filter: bool


def decimal_value(row: Dict[str, str], key: str) -> Decimal:
    value = row.get(key)
    if value in (None, "", "NULL"):
        return Decimal("0")
    return Decimal(value)


def pct(value: Decimal) -> str:
    return f"{(value * Decimal('100')).quantize(Decimal('0.01'))}%"


def money(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01'))}元"


def month_bounds(year: int, start_month: int, end_month: int) -> Tuple[str, str]:
    if end_month == 12:
        end = f"{year + 1}-01-01"
    else:
        end = f"{year}-{end_month + 1:02d}-01"
    return f"{year}-{start_month:02d}-01", end


def parse_time_conditions(question: str) -> Tuple[List[str], List[str], List[str]]:
    sales_conditions = []
    customer_conditions = []
    labels = []

    match = re.search(r"(20\d{2})\s*年\s*(\d{1,2})\s*月?\s*(?:-|到|至|~)\s*(\d{1,2})\s*月", question)
    if match:
        year, start_month, end_month = map(int, match.groups())
        start, end = month_bounds(year, start_month, end_month)
        labels.append(f"{year}年{start_month}月至{end_month}月")
    else:
        match = re.search(r"(20\d{2})\s*年\s*(\d{1,2})\s*月", question)
        if match:
            year, month = map(int, match.groups())
            start, end = month_bounds(year, month, month)
            labels.append(f"{year}年{month}月")
        else:
            match = re.search(r"(20\d{2})\s*年", question)
            if match:
                year = int(match.group(1))
                start, end = f"{year}-01-01", f"{year + 1}-01-01"
                labels.append(f"{year}年")
            else:
                return sales_conditions, customer_conditions, labels

    sales_conditions.append(f"`order_date` >= {quote_literal(start)} AND `order_date` < {quote_literal(end)}")
    customer_conditions.append(f"`stat_month` >= {quote_literal(start)} AND `stat_month` < {quote_literal(end)}")
    return sales_conditions, customer_conditions, labels


def load_distinct_values(db: MysqlCli, table: str, fields: Iterable[str]) -> Dict[str, List[str]]:
    values: Dict[str, List[str]] = {}
    for field in fields:
        rows = db.query(
            f"SELECT DISTINCT {quote_ident(field)} AS value "
            f"FROM {quote_ident(table)} ORDER BY {quote_ident(field)}"
        )
        values[field] = [row["value"] for row in rows if row.get("value")]
    return values


def build_scope(db: MysqlCli, question: str) -> Scope:
    sales_conditions, customer_conditions, labels = parse_time_conditions(question)
    dimension_names = {"区域", "部门", "产品类别", "产品名称", "渠道", "客户类型", "时间", "月份"}
    sales_only_dims = {"部门", "产品类别", "产品名称", "渠道"}
    has_sales_only_filter = False

    sales_fields = {
        "region": "区域",
        "department": "部门",
        "product_category": "产品类别",
        "product_name": "产品名称",
        "channel": "渠道",
        "customer_type": "客户类型",
    }
    customer_fields = {
        "region": "区域",
        "customer_type": "客户类型",
    }

    sales_values = load_distinct_values(db, "sales_order", sales_fields.keys())
    for field, dim_name in sales_fields.items():
        for value in sales_values.get(field, []):
            if value in dimension_names:
                continue
            if value in question:
                sales_conditions.append(f"{quote_ident(field)} = {quote_literal(value)}")
                labels.append(f"{dim_name}={value}")
                if dim_name in sales_only_dims:
                    has_sales_only_filter = True

    customer_values = load_distinct_values(db, "customer_profile", customer_fields.keys())
    for field, dim_name in customer_fields.items():
        for value in customer_values.get(field, []):
            if value in dimension_names:
                continue
            if value in question:
                customer_conditions.append(f"{quote_ident(field)} = {quote_literal(value)}")

    return Scope(
        question=question,
        sales_conditions=list(dict.fromkeys(sales_conditions)),
        customer_conditions=list(dict.fromkeys(customer_conditions)),
        labels=list(dict.fromkeys(labels)),
        has_sales_only_filter=has_sales_only_filter,
    )


def where_clause(conditions: Sequence[str]) -> str:
    if not conditions:
        return ""
    return " WHERE " + " AND ".join(conditions)


def load_facts(db: MysqlCli, scope: Scope) -> Dict[str, object]:
    sales_where = where_clause(scope.sales_conditions)
    customer_where = where_clause(scope.customer_conditions)
    overview = db.query(
        f"""
        SELECT
          SUM(sales_amount) AS sales,
          SUM(target_amount) AS target,
          SUM(gross_profit) AS gross_profit,
          SUM(gross_profit) / SUM(sales_amount) AS gross_margin_rate,
          SUM(sales_amount) / SUM(target_amount) AS target_achievement_rate,
          SUM(order_count) AS order_count,
          SUM(customer_count) AS customer_count
        FROM sales_order
        {sales_where}
        """
    )[0]
    months = db.query(
        f"""
        SELECT
          DATE_FORMAT(order_date, '%Y-%m') AS month,
          SUM(sales_amount) AS sales,
          SUM(gross_profit) / SUM(sales_amount) AS gross_margin_rate,
          SUM(sales_amount) / SUM(target_amount) AS target_achievement_rate
        FROM sales_order
        {sales_where}
        GROUP BY DATE_FORMAT(order_date, '%Y-%m')
        ORDER BY month
        """
    )
    regions = db.query(
        f"""
        SELECT
          region,
          SUM(sales_amount) AS sales,
          SUM(target_amount) AS target,
          SUM(sales_amount) / SUM(target_amount) AS target_achievement_rate,
          SUM(gross_profit) / SUM(sales_amount) AS gross_margin_rate
        FROM sales_order
        {sales_where}
        GROUP BY region
        ORDER BY sales DESC
        """
    )
    channels = db.query(
        f"""
        SELECT
          channel,
          SUM(sales_amount) AS sales,
          SUM(gross_profit) / SUM(sales_amount) AS gross_margin_rate
        FROM sales_order
        {sales_where}
        GROUP BY channel
        ORDER BY sales DESC
        """
    )
    products = db.query(
        f"""
        SELECT
          product_category,
          SUM(sales_amount) AS sales,
          SUM(gross_profit) / SUM(sales_amount) AS gross_margin_rate
        FROM sales_order
        {sales_where}
        GROUP BY product_category
        ORDER BY sales DESC
        """
    )
    if scope.has_sales_only_filter:
        retention = []
    else:
        retention = db.query(
            f"""
            SELECT
              DATE_FORMAT(stat_month, '%Y-%m') AS month,
              SUM(new_customers) AS new_customers,
              SUM(active_customers) AS active_customers,
              SUM(retained_customers) / SUM(active_customers) AS retention_rate,
              SUM(churned_customers) AS churned_customers
            FROM customer_profile
            {customer_where}
            GROUP BY DATE_FORMAT(stat_month, '%Y-%m')
            ORDER BY month
            """
        )
    return {
        "overview": overview,
        "months": months,
        "regions": regions,
        "channels": channels,
        "products": products,
        "retention": retention,
        "scope": asdict(scope),
    }


def build_advices(facts: Dict[str, object]) -> List[Advice]:
    overview = facts["overview"]
    months = facts["months"]
    regions = facts["regions"]
    channels = facts["channels"]
    products = facts["products"]
    retention = facts["retention"]

    advices: List[Advice] = []
    achievement = decimal_value(overview, "target_achievement_rate")
    margin = decimal_value(overview, "gross_margin_rate")

    if achievement >= Decimal("1.05"):
        advices.append(
            Advice(
                priority="高",
                theme="增长目标",
                decision="适度上调下一周期销售目标，并优先复制高完成区域的打法。",
                reason=f"整体目标完成率为{pct(achievement)}，已经超过105%的积极阈值。",
                actions=[
                    "将高完成区域的渠道、产品和客户打法整理为标准销售动作。",
                    "下一周期目标可以分区域差异化上调，避免一刀切加压。",
                    "同步监控毛利率，防止单纯追求规模导致盈利质量下滑。",
                ],
            )
        )
    elif achievement < Decimal("0.95"):
        advices.append(
            Advice(
                priority="高",
                theme="目标补差",
                decision="启动目标补差机制，优先处理未达标区域和部门。",
                reason=f"整体目标完成率为{pct(achievement)}，低于95%的预警阈值。",
                actions=[
                    "拆解未达标区域的客户、渠道和产品缺口。",
                    "对低完成团队设置周度跟进节奏。",
                    "优先推进转化周期短、毛利稳定的机会。",
                ],
            )
        )

    if months:
        first = decimal_value(months[0], "sales")
        last = decimal_value(months[-1], "sales")
        if first and last > first:
            growth = (last - first) / first
            advices.append(
                Advice(
                    priority="中",
                    theme="销售趋势",
                    decision="保持当前增长节奏，重点把月度增长沉淀为稳定获客能力。",
                    reason=f"销售额从{months[0]['month']}的{money(first)}增长到{months[-1]['month']}的{money(last)}，增幅为{pct(growth)}。",
                    actions=[
                        "识别最近两个月贡献增长的主要渠道和产品。",
                        "将新增线索、转化率、客单价拆成过程指标持续跟踪。",
                        "对增长较快业务设置交付和服务容量预警。",
                    ],
                )
            )

    if regions:
        top_region = regions[0]
        bottom_region = sorted(regions, key=lambda row: decimal_value(row, "target_achievement_rate"))[0]
        advices.append(
            Advice(
                priority="高",
                theme="区域经营",
                decision=f"优先复盘{top_region['region']}区域打法，并关注{bottom_region['region']}区域目标完成质量。",
                reason=(
                    f"{top_region['region']}销售额最高，为{money(decimal_value(top_region, 'sales'))}；"
                    f"{bottom_region['region']}目标完成率相对最低，为{pct(decimal_value(bottom_region, 'target_achievement_rate'))}。"
                ),
                actions=[
                    f"提炼{top_region['region']}在客户、渠道和产品组合上的成功因素。",
                    f"检查{bottom_region['region']}的目标设定、机会储备和转化效率。",
                    "将区域目标完成率和毛利率一起看，避免只看规模排名。",
                ],
            )
        )

    if channels:
        top_channel = channels[0]
        low_margin_channel = sorted(channels, key=lambda row: decimal_value(row, "gross_margin_rate"))[0]
        advices.append(
            Advice(
                priority="中",
                theme="渠道策略",
                decision=f"继续加大{top_channel['channel']}渠道投入，同时优化{low_margin_channel['channel']}渠道的利润结构。",
                reason=(
                    f"{top_channel['channel']}渠道销售额最高，为{money(decimal_value(top_channel, 'sales'))}；"
                    f"{low_margin_channel['channel']}渠道毛利率相对最低，为{pct(decimal_value(low_margin_channel, 'gross_margin_rate'))}。"
                ),
                actions=[
                    f"分析{top_channel['channel']}渠道的线索来源和转化动作，评估可复制性。",
                    f"复核{low_margin_channel['channel']}渠道折扣、交付成本和产品结构。",
                    "按渠道建立销售额、毛利率、客户数的组合看板。",
                ],
            )
        )

    if products:
        top_product = products[0]
        low_margin_product = sorted(products, key=lambda row: decimal_value(row, "gross_margin_rate"))[0]
        advices.append(
            Advice(
                priority="中",
                theme="产品组合",
                decision=f"围绕{top_product['product_category']}巩固收入基本盘，并改善{low_margin_product['product_category']}的盈利表现。",
                reason=(
                    f"{top_product['product_category']}销售额最高，为{money(decimal_value(top_product, 'sales'))}；"
                    f"{low_margin_product['product_category']}毛利率相对最低，为{pct(decimal_value(low_margin_product, 'gross_margin_rate'))}。"
                ),
                actions=[
                    f"将{top_product['product_category']}作为重点交叉销售入口。",
                    f"检查{low_margin_product['product_category']}的定价、交付投入和客户结构。",
                    "对产品类别设置收入贡献和毛利贡献双维度排序。",
                ],
            )
        )

    if retention:
        latest = retention[-1]
        retention_rate = decimal_value(latest, "retention_rate")
        churned = decimal_value(latest, "churned_customers")
        priority = "高" if retention_rate < Decimal("0.83") else "中"
        advices.append(
            Advice(
                priority=priority,
                theme="客户运营",
                decision="持续提升客户留存，并对流失客户建立召回和预警机制。",
                reason=f"{latest['month']}客户留存率为{pct(retention_rate)}，流失客户数为{churned}。",
                actions=[
                    "对流失客户按区域和客户类型拆解，定位流失集中点。",
                    "对高价值活跃客户设置续约、复购或增购触达计划。",
                    "将客户留存率纳入月度经营复盘，不只看新增客户数。",
                ],
            )
        )

    if margin < Decimal("0.32"):
        advices.append(
            Advice(
                priority="高",
                theme="盈利质量",
                decision="暂停低毛利扩张动作，优先修复毛利率。",
                reason=f"整体毛利率为{pct(margin)}，低于32%的风险阈值。",
                actions=[
                    "排查低毛利产品和渠道组合。",
                    "对高折扣订单设置审批规则。",
                    "提高标准化交付比例，降低定制成本。",
                ],
            )
        )

    priority_order = {"高": 0, "中": 1, "低": 2}
    return sorted(advices, key=lambda item: priority_order.get(item.priority, 9))


def render_markdown(facts: Dict[str, object], advices: List[Advice]) -> str:
    overview = facts["overview"]
    scope = facts.get("scope", {})
    labels = scope.get("labels", []) if isinstance(scope, dict) else []
    scope_text = "、".join(labels) if labels else "全量数据"
    lines = [
        "# 决策意见",
        "",
        f"- 分析范围：{scope_text}",
        "",
        "## 指标概览",
        "",
        f"- 销售额：{money(decimal_value(overview, 'sales'))}",
        f"- 目标完成率：{pct(decimal_value(overview, 'target_achievement_rate'))}",
        f"- 毛利率：{pct(decimal_value(overview, 'gross_margin_rate'))}",
        f"- 订单数：{decimal_value(overview, 'order_count')}",
        f"- 客户数：{decimal_value(overview, 'customer_count')}",
        "",
        "## 建议",
        "",
    ]
    for index, advice in enumerate(advices, start=1):
        lines.append(f"### {index}. [{advice.priority}] {advice.theme}")
        lines.append("")
        lines.append(f"**决策建议**：{advice.decision}")
        lines.append("")
        lines.append(f"**依据**：{advice.reason}")
        lines.append("")
        lines.append("**行动项**：")
        for action in advice.actions:
            lines.append(f"- {action}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_kpis(facts: Dict[str, object]) -> List[Dict[str, str]]:
    overview = facts["overview"]
    achievement = decimal_value(overview, "target_achievement_rate")
    margin = decimal_value(overview, "gross_margin_rate")
    achievement_status = "success" if achievement >= Decimal("1.0") else "warning"
    margin_status = "success" if margin >= Decimal("0.35") else "warning"
    return [
        kpi("销售额", money(decimal_value(overview, "sales")), status="neutral"),
        kpi("目标完成率", pct(achievement), status=achievement_status),
        kpi("毛利率", pct(margin), status=margin_status),
        kpi("订单数", str(decimal_value(overview, "order_count")), status="neutral"),
        kpi("客户数", str(decimal_value(overview, "customer_count")), status="neutral"),
    ]


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate ChatBI decision advice")
    parser.add_argument("question_terms", nargs="*", help="Optional Chinese scope, such as 华东2026年4月决策建议")
    parser.add_argument("--question", help="Optional Chinese scope; overrides positional question")
    parser.add_argument("--json", action="store_true", help="print structured JSON")
    parser.add_argument("--host", default=DEFAULT_DB["host"])
    parser.add_argument("--port", default=DEFAULT_DB["port"])
    parser.add_argument("--user", default=DEFAULT_DB["user"])
    parser.add_argument("--password", default=DEFAULT_DB["password"])
    parser.add_argument("--database", default=DEFAULT_DB["database"])
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    config = {
        "host": args.host,
        "port": str(args.port),
        "user": args.user,
        "password": args.password,
        "database": args.database,
    }
    db = MysqlCli(config)
    question = args.question if args.question is not None else " ".join(args.question_terms)
    try:
        scope = build_scope(db, question)
        facts = load_facts(db, scope)
        advices = build_advices(facts)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.json:
        data = {"facts": facts, "advices": [asdict(item) for item in advices]}
        payload = skill_response(
            kind="decision",
            text=render_markdown(facts, advices),
            data=data,
            kpis=build_kpis(facts),
        )
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(facts, advices))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
