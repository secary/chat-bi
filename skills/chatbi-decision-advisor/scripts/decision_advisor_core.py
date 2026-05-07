from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
import json
import re
from typing import Dict, Iterable, List, Sequence, Tuple

from _shared.db import MysqlCli, quote_ident, quote_literal
from _shared.output import kpi, skill_response


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
    focus_dimensions: List[str]
    focus_metrics: List[str]


METRIC_PATTERNS = {
    "销售额": ["销售额", "营收", "收入", "业绩"],
    "目标完成率": ["目标完成率", "达成率", "完成率", "目标达成"],
    "毛利率": ["毛利率", "利润率"],
    "毛利": ["毛利", "利润额"],
    "客户留存": ["留存", "留存率", "流失", "召回", "复购"],
    "客户数": ["客户数", "客户量", "客户规模"],
    "订单数": ["订单数", "单量", "订单量"],
}

DIMENSION_PATTERNS = {
    "区域": ["区域", "大区", "地区", "片区", "市场"],
    "渠道": ["渠道", "成交渠道", "获客渠道", "销售渠道", "来源渠道"],
    "产品类别": ["产品类别", "产品线", "品类", "业务线", "产品分类", "产品类型"],
    "产品名称": ["产品名称", "产品名", "具体产品", "服务名称"],
    "部门": ["部门", "团队", "组织", "业务部门"],
    "客户类型": ["客户类型", "客户类别", "客户分层", "客群"],
    "月份": ["月份", "时间", "按月", "月度", "趋势", "环比", "同比"],
}

THEME_DIMENSION_MAP = {
    "销售趋势": "月份",
    "区域经营": "区域",
    "渠道策略": "渠道",
    "产品组合": "产品类别",
}

THEME_METRIC_MAP = {
    "增长目标": {"销售额", "目标完成率"},
    "目标补差": {"销售额", "目标完成率"},
    "销售趋势": {"销售额", "目标完成率", "毛利率", "毛利"},
    "区域经营": {"销售额", "目标完成率", "毛利率", "毛利"},
    "渠道策略": {"销售额", "毛利率", "毛利"},
    "产品组合": {"销售额", "毛利率", "毛利"},
    "客户运营": {"客户留存", "客户数"},
    "盈利质量": {"毛利率", "毛利"},
}


def decimal_value(row: Dict[str, str], key: str) -> Decimal:
    value = row.get(key)
    return Decimal("0") if value in (None, "", "NULL") else Decimal(value)


def pct(value: Decimal) -> str:
    return f"{(value * Decimal('100')).quantize(Decimal('0.01'))}%"


def money(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01'))}元"


def month_bounds(year: int, start_month: int, end_month: int) -> Tuple[str, str]:
    end = f"{year + 1}-01-01" if end_month == 12 else f"{year}-{end_month + 1:02d}-01"
    return f"{year}-{start_month:02d}-01", end


def parse_time_conditions(question: str) -> Tuple[List[str], List[str], List[str]]:
    sales_conditions: List[str] = []
    customer_conditions: List[str] = []
    labels: List[str] = []
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
            if not match:
                return sales_conditions, customer_conditions, labels
            year = int(match.group(1))
            start, end = f"{year}-01-01", f"{year + 1}-01-01"
            labels.append(f"{year}年")
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


def parse_focus_dimensions(question: str) -> List[str]:
    return [name for name, words in DIMENSION_PATTERNS.items() if any(word in question for word in words)]


def parse_focus_metrics(question: str) -> List[str]:
    return [name for name, words in METRIC_PATTERNS.items() if any(word in question for word in words)]


def build_scope(db: MysqlCli, question: str) -> Scope:
    sales_conditions, customer_conditions, labels = parse_time_conditions(question)
    dimension_names = {"区域", "部门", "产品类别", "产品名称", "渠道", "客户类型", "时间", "月份"}
    sales_only_dims = {"部门", "产品类别", "产品名称", "渠道"}
    sales_fields = {
        "region": "区域",
        "department": "部门",
        "product_category": "产品类别",
        "product_name": "产品名称",
        "channel": "渠道",
        "customer_type": "客户类型",
    }
    customer_fields = {"region": "区域", "customer_type": "客户类型"}
    has_sales_only_filter = False

    for field, dim_name in sales_fields.items():
        for value in load_distinct_values(db, "sales_order", [field]).get(field, []):
            if value in dimension_names or value not in question:
                continue
            sales_conditions.append(f"{quote_ident(field)} = {quote_literal(value)}")
            labels.append(f"{dim_name}={value}")
            has_sales_only_filter = has_sales_only_filter or dim_name in sales_only_dims

    for field, dim_name in customer_fields.items():
        for value in load_distinct_values(db, "customer_profile", [field]).get(field, []):
            if value in dimension_names or value not in question:
                continue
            customer_conditions.append(f"{quote_ident(field)} = {quote_literal(value)}")
            if f"{dim_name}={value}" not in labels:
                labels.append(f"{dim_name}={value}")

    return Scope(
        question=question,
        sales_conditions=list(dict.fromkeys(sales_conditions)),
        customer_conditions=list(dict.fromkeys(customer_conditions)),
        labels=list(dict.fromkeys(labels)),
        has_sales_only_filter=has_sales_only_filter,
        focus_dimensions=list(dict.fromkeys(parse_focus_dimensions(question))),
        focus_metrics=list(dict.fromkeys(parse_focus_metrics(question))),
    )


def where_clause(conditions: Sequence[str]) -> str:
    return "" if not conditions else " WHERE " + " AND ".join(conditions)


def load_facts(db: MysqlCli, scope: Scope) -> Dict[str, object]:
    sales_where = where_clause(scope.sales_conditions)
    customer_where = where_clause(scope.customer_conditions)
    retention = [] if scope.has_sales_only_filter else db.query(
        f"""
        SELECT DATE_FORMAT(stat_month, '%Y-%m') AS month, SUM(new_customers) AS new_customers,
               SUM(active_customers) AS active_customers,
               SUM(retained_customers) / SUM(active_customers) AS retention_rate,
               SUM(churned_customers) AS churned_customers
        FROM customer_profile{customer_where}
        GROUP BY DATE_FORMAT(stat_month, '%Y-%m') ORDER BY month
        """
    )
    return {
        "overview": db.query(
            f"""
            SELECT SUM(sales_amount) AS sales, SUM(target_amount) AS target, SUM(gross_profit) AS gross_profit,
                   SUM(gross_profit) / SUM(sales_amount) AS gross_margin_rate,
                   SUM(sales_amount) / SUM(target_amount) AS target_achievement_rate,
                   SUM(order_count) AS order_count, SUM(customer_count) AS customer_count
            FROM sales_order{sales_where}
            """
        )[0],
        "months": db.query(
            f"""
            SELECT DATE_FORMAT(order_date, '%Y-%m') AS month, SUM(sales_amount) AS sales,
                   SUM(gross_profit) / SUM(sales_amount) AS gross_margin_rate,
                   SUM(sales_amount) / SUM(target_amount) AS target_achievement_rate
            FROM sales_order{sales_where}
            GROUP BY DATE_FORMAT(order_date, '%Y-%m') ORDER BY month
            """
        ),
        "regions": db.query(
            f"""
            SELECT region, SUM(sales_amount) AS sales, SUM(target_amount) AS target,
                   SUM(sales_amount) / SUM(target_amount) AS target_achievement_rate,
                   SUM(gross_profit) / SUM(sales_amount) AS gross_margin_rate
            FROM sales_order{sales_where}
            GROUP BY region ORDER BY sales DESC
            """
        ),
        "channels": db.query(
            f"""
            SELECT channel, SUM(sales_amount) AS sales,
                   SUM(gross_profit) / SUM(sales_amount) AS gross_margin_rate
            FROM sales_order{sales_where}
            GROUP BY channel ORDER BY sales DESC
            """
        ),
        "products": db.query(
            f"""
            SELECT product_category, SUM(sales_amount) AS sales,
                   SUM(gross_profit) / SUM(sales_amount) AS gross_margin_rate
            FROM sales_order{sales_where}
            GROUP BY product_category ORDER BY sales DESC
            """
        ),
        "retention": retention,
        "scope": asdict(scope),
    }


def _theme_enabled(scope: Dict[str, object], theme: str) -> bool:
    focus_dimensions = set(scope.get("focus_dimensions", [])) if isinstance(scope, dict) else set()
    focus_metrics = set(scope.get("focus_metrics", [])) if isinstance(scope, dict) else set()
    if focus_dimensions and theme == "客户运营" and not ({"客户类型", "区域", "月份"} & focus_dimensions):
        return False
    dimension = THEME_DIMENSION_MAP.get(theme)
    if focus_dimensions and dimension and dimension not in focus_dimensions:
        return False
    if focus_metrics and not (THEME_METRIC_MAP.get(theme, set()) & focus_metrics):
        return False
    return True


def build_advices(facts: Dict[str, object]) -> List[Advice]:
    overview, months = facts["overview"], facts["months"]
    regions, channels = facts["regions"], facts["channels"]
    products, retention = facts["products"], facts["retention"]
    scope = facts.get("scope", {})
    achievement = decimal_value(overview, "target_achievement_rate")
    margin = decimal_value(overview, "gross_margin_rate")
    advices: List[Advice] = []

    if _theme_enabled(scope, "增长目标") and achievement >= Decimal("1.05"):
        advices.append(Advice("高", "增长目标", "适度上调下一周期销售目标，并优先复制高完成区域的打法。", f"整体目标完成率为{pct(achievement)}，已经超过105%的积极阈值。", ["将高完成区域的渠道、产品和客户打法整理为标准销售动作。", "下一周期目标可以分区域差异化上调，避免一刀切加压。", "同步监控毛利率，防止单纯追求规模导致盈利质量下滑。"]))
    if _theme_enabled(scope, "目标补差") and achievement < Decimal("0.95"):
        advices.append(Advice("高", "目标补差", "启动目标补差机制，优先处理未达标区域和部门。", f"整体目标完成率为{pct(achievement)}，低于95%的预警阈值。", ["拆解未达标区域的客户、渠道和产品缺口。", "对低完成团队设置周度跟进节奏。", "优先推进转化周期短、毛利稳定的机会。"]))
    if _theme_enabled(scope, "销售趋势") and len(months) >= 2:
        first, last = decimal_value(months[0], "sales"), decimal_value(months[-1], "sales")
        if first and last > first:
            growth = (last - first) / first
            advices.append(Advice("中", "销售趋势", "保持当前增长节奏，重点把月度增长沉淀为稳定获客能力。", f"销售额从{months[0]['month']}的{money(first)}增长到{months[-1]['month']}的{money(last)}，增幅为{pct(growth)}。", ["识别最近两个月贡献增长的主要渠道和产品。", "将新增线索、转化率、客单价拆成过程指标持续跟踪。", "对增长较快业务设置交付和服务容量预警。"]))
    if _theme_enabled(scope, "区域经营") and regions:
        top_region = regions[0]
        bottom_region = min(regions, key=lambda row: decimal_value(row, "target_achievement_rate"))
        advices.append(Advice("高", "区域经营", f"优先复盘{top_region['region']}区域打法，并关注{bottom_region['region']}区域目标完成质量。", f"{top_region['region']}销售额最高，为{money(decimal_value(top_region, 'sales'))}；{bottom_region['region']}目标完成率相对最低，为{pct(decimal_value(bottom_region, 'target_achievement_rate'))}。", [f"提炼{top_region['region']}在客户、渠道和产品组合上的成功因素。", f"检查{bottom_region['region']}的目标设定、机会储备和转化效率。", "将区域目标完成率和毛利率一起看，避免只看规模排名。"]))
    if _theme_enabled(scope, "渠道策略") and channels:
        top_channel = channels[0]
        low_margin_channel = min(channels, key=lambda row: decimal_value(row, "gross_margin_rate"))
        advices.append(Advice("中", "渠道策略", f"继续加大{top_channel['channel']}渠道投入，同时优化{low_margin_channel['channel']}渠道的利润结构。", f"{top_channel['channel']}渠道销售额最高，为{money(decimal_value(top_channel, 'sales'))}；{low_margin_channel['channel']}渠道毛利率相对最低，为{pct(decimal_value(low_margin_channel, 'gross_margin_rate'))}。", [f"分析{top_channel['channel']}渠道的线索来源和转化动作，评估可复制性。", f"复核{low_margin_channel['channel']}渠道折扣、交付成本和产品结构。", "按渠道建立销售额、毛利率、客户数的组合看板。"]))
    if _theme_enabled(scope, "产品组合") and products:
        top_product = products[0]
        low_margin_product = min(products, key=lambda row: decimal_value(row, "gross_margin_rate"))
        advices.append(Advice("中", "产品组合", f"围绕{top_product['product_category']}巩固收入基本盘，并改善{low_margin_product['product_category']}的盈利表现。", f"{top_product['product_category']}销售额最高，为{money(decimal_value(top_product, 'sales'))}；{low_margin_product['product_category']}毛利率相对最低，为{pct(decimal_value(low_margin_product, 'gross_margin_rate'))}。", [f"将{top_product['product_category']}作为重点交叉销售入口。", f"检查{low_margin_product['product_category']}的定价、交付投入和客户结构。", "对产品类别设置收入贡献和毛利贡献双维度排序。"]))
    if _theme_enabled(scope, "客户运营") and retention:
        latest = retention[-1]
        retention_rate = decimal_value(latest, "retention_rate")
        advices.append(Advice("高" if retention_rate < Decimal("0.83") else "中", "客户运营", "持续提升客户留存，并对流失客户建立召回和预警机制。", f"{latest['month']}客户留存率为{pct(retention_rate)}，流失客户数为{decimal_value(latest, 'churned_customers')}。", ["对流失客户按区域和客户类型拆解，定位流失集中点。", "对高价值活跃客户设置续约、复购或增购触达计划。", "将客户留存率纳入月度经营复盘，不只看新增客户数。"]))
    if _theme_enabled(scope, "盈利质量") and margin < Decimal("0.32"):
        advices.append(Advice("高", "盈利质量", "暂停低毛利扩张动作，优先修复毛利率。", f"整体毛利率为{pct(margin)}，低于32%的风险阈值。", ["排查低毛利产品和渠道组合。", "对高折扣订单设置审批规则。", "提高标准化交付比例，降低定制成本。"]))
    return sorted(advices, key=lambda item: {"高": 0, "中": 1, "低": 2}.get(item.priority, 9))


def render_markdown(facts: Dict[str, object], advices: List[Advice]) -> str:
    overview = facts["overview"]
    scope = facts.get("scope", {})
    labels = scope.get("labels", []) if isinstance(scope, dict) else []
    scope_text = "、".join(labels) if labels else "全量数据"
    lines = ["# 决策意见", "", f"- 分析范围：{scope_text}", "", "## 指标概览", "", f"- 销售额：{money(decimal_value(overview, 'sales'))}", f"- 目标完成率：{pct(decimal_value(overview, 'target_achievement_rate'))}", f"- 毛利率：{pct(decimal_value(overview, 'gross_margin_rate'))}", f"- 订单数：{decimal_value(overview, 'order_count')}", f"- 客户数：{decimal_value(overview, 'customer_count')}", "", "## 建议", ""]
    if not advices:
        lines.extend(["- 当前问题范围内未触发专门规则，建议先补充关注指标或维度后再生成经营建议。", ""])
    for index, advice in enumerate(advices, start=1):
        lines.extend([f"### {index}. [{advice.priority}] {advice.theme}", "", f"**决策建议**：{advice.decision}", "", f"**依据**：{advice.reason}", "", "**行动项**："])
        lines.extend([f"- {action}" for action in advice.actions])
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_kpis(facts: Dict[str, object]) -> List[Dict[str, str]]:
    overview = facts["overview"]
    achievement = decimal_value(overview, "target_achievement_rate")
    margin = decimal_value(overview, "gross_margin_rate")
    return [kpi("销售额", money(decimal_value(overview, "sales")), status="neutral"), kpi("目标完成率", pct(achievement), status="success" if achievement >= Decimal("1.0") else "warning"), kpi("毛利率", pct(margin), status="success" if margin >= Decimal("0.35") else "warning"), kpi("订单数", str(decimal_value(overview, "order_count")), status="neutral"), kpi("客户数", str(decimal_value(overview, "customer_count")), status="neutral")]


def build_payload(facts: Dict[str, object], advices: List[Advice]) -> Dict[str, object]:
    return skill_response(kind="decision", text=render_markdown(facts, advices), data={"facts": facts, "advices": [asdict(item) for item in advices]}, kpis=build_kpis(facts))


def dump_payload(payload: Dict[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)
