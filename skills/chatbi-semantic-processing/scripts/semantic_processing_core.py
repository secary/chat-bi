from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class MetricDef:
    metric_id: str
    name: str
    domain: str
    aggregation: str
    unit: Optional[str]
    formula: Optional[str] = None
    requires_business_line: bool = False


METRICS: List[Tuple[MetricDef, Tuple[str, ...]]] = [
    (MetricDef("corporate_deposit_balance", "对公存款余额", "deposit", "sum", "CNY"), ("对公存款余额", "公司存款余额", "企业存款余额", "对公存款规模")),
    (MetricDef("retail_deposit_balance", "个人存款余额", "deposit", "sum", "CNY"), ("个人存款余额", "零售存款余额", "储蓄存款余额", "个人存款规模")),
    (MetricDef("deposit_balance", "存款余额", "deposit", "sum", "CNY", requires_business_line=True), ("存款余额", "存款规模", "存款额", "存款总额", "时点存款")),
    (MetricDef("corporate_loan_balance", "对公贷款余额", "loan", "sum", "CNY"), ("对公贷款余额", "企业贷款余额", "对公信贷余额")),
    (MetricDef("retail_loan_balance", "个人贷款余额", "loan", "sum", "CNY"), ("个人贷款余额", "零售贷款余额", "个贷余额")),
    (MetricDef("inclusive_loan_balance", "普惠贷款余额", "loan", "sum", "CNY"), ("普惠贷款余额", "小微贷款余额", "普惠金融贷款余额")),
    (MetricDef("loan_balance", "贷款余额", "loan", "sum", "CNY", requires_business_line=True), ("贷款余额", "贷款规模", "信贷余额")),
    (MetricDef("corporate_customer_count", "对公客户数", "customer", "count_distinct", None), ("对公客户数", "企业客户数", "公司客户数")),
    (MetricDef("retail_customer_count", "个人客户数", "customer", "count_distinct", None), ("个人客户数", "零售客户数", "储蓄客户数")),
    (MetricDef("customer_count", "客户数", "customer", "count_distinct", None, requires_business_line=True), ("客户数", "客户数量", "户数")),
    (MetricDef("new_customer_count", "新增客户数", "customer", "count_distinct", None, requires_business_line=True), ("新增客户数", "新客户", "拉新客户", "新开户客户数")),
    (MetricDef("active_customer_count", "活跃客户数", "customer", "count_distinct", None, requires_business_line=True), ("活跃客户数", "活客数", "动户客户")),
    (MetricDef("mobile_active_user_count", "手机银行活跃用户数", "channel", "count_distinct", None), ("手机银行活跃用户数", "手机银行活客", "掌银活跃用户", "月活用户", "mau")),
    (MetricDef("transaction_amount", "交易金额", "transaction", "sum", "CNY"), ("交易金额", "交易额", "流水金额", "支付金额")),
    (MetricDef("transaction_count", "交易笔数", "transaction", "count", None), ("交易笔数", "笔数", "交易次数")),
    (MetricDef("aum_balance", "AUM余额", "wealth", "sum", "CNY"), ("aum余额", "aum", "金融资产余额", "客户资产余额")),
    (MetricDef("fee_income", "中间业务收入", "income", "sum", "CNY"), ("中间业务收入", "手续费收入", "中收", "非息收入")),
    (MetricDef("interest_income", "利息收入", "income", "sum", "CNY"), ("利息收入", "息收", "贷款利息收入")),
    (MetricDef("npl_ratio", "不良贷款率", "risk", "ratio", None, formula="不良贷款余额 / 贷款余额"), ("不良贷款率", "不良率", "贷款不良率")),
]

DIMENSIONS: List[Tuple[str, str, Tuple[str, ...]]] = [
    ("branch", "机构", ("支行", "网点", "分行", "营业部", "机构")),
    ("region", "地区", ("区域", "地区", "城市", "省份")),
    ("channel", "渠道", ("渠道", "交易渠道", "来源渠道", "办理渠道")),
    ("product", "产品", ("产品", "产品名称", "产品线", "业务品种")),
    ("customer_type", "客户类型", ("客户类型", "客群", "客户类别")),
    ("time", "时间", ("按月", "每月", "趋势", "走势", "月份", "时间")),
]

BUSINESS_LINES: List[Tuple[str, Tuple[str, ...]]] = [
    ("corporate", ("对公", "公司", "企业", "单位客户", "机构客户")),
    ("retail", ("个人", "零售", "私人客户", "储蓄客户")),
    ("inclusive_finance", ("普惠", "小微", "个体工商户", "涉农")),
    ("financial_markets", ("同业", "金融市场", "资金业务", "票据业务", "债券业务")),
]


def parse_question(question: str, today: Optional[date] = None) -> Dict[str, Any]:
    current = today or date.today()
    text = question.strip()
    normalized = re.sub(r"\s+", "", text).lower()
    business_line = _detect_business_line(normalized)
    metric = _detect_metric(normalized, business_line)
    dimensions = _detect_dimensions(normalized)
    time_info, assumptions = _parse_time(normalized, current)
    intent_type = _detect_intent_type(normalized)
    comparison = _build_comparison(normalized)
    limit = _parse_limit(normalized)
    missing_slots, questions, ambiguities = _collect_gaps(
        normalized, metric, business_line, dimensions, limit
    )
    if intent_type == "trend" and not any(item["dimension_id"] == "time" for item in dimensions):
        dimensions.append({"dimension_id": "time", "name": "时间", "role": "group_by"})

    query_intent = {
        "status": "ready" if not missing_slots else "need_clarification",
        "original_query": text,
        "language": "zh-CN",
        "business_line": business_line,
        "domain": metric.domain if metric else _infer_domain(normalized),
        "intent_type": intent_type,
        "metrics": [_metric_payload(metric)] if metric else [],
        "dimensions": dimensions,
        "filters": [],
        "time": time_info,
        "comparison": comparison,
        "sort": _build_sort(intent_type, metric),
        "limit": limit,
        "missing_slots": missing_slots,
        "clarification_questions": questions,
        "ambiguities": ambiguities,
        "assumptions": assumptions,
        "sql_readiness": {
            "ready_for_text_to_sql": not missing_slots,
            "schema_hints": _schema_hints(metric, dimensions),
            "notes": [] if not missing_slots else ["仍存在关键语义槽位缺失，暂不建议直接生成 SQL。"],
        },
    }
    return query_intent


def render_summary(query_intent: Dict[str, Any]) -> str:
    if query_intent["status"] == "ready":
        metric_names = "、".join(item["name"] for item in query_intent["metrics"]) or "未识别指标"
        return f"语义解析完成：已识别 {metric_names}，可进入后续查询规划。"
    question = query_intent["clarification_questions"][0] if query_intent["clarification_questions"] else "需要补充业务口径。"
    return f"语义解析需要澄清：{question}"


def _detect_business_line(normalized: str) -> str:
    for business_line, words in BUSINESS_LINES:
        if any(word in normalized for word in words):
            return business_line
    return "unknown"


def _detect_metric(normalized: str, business_line: str) -> Optional[MetricDef]:
    candidates: List[Tuple[int, MetricDef]] = []
    for metric, words in METRICS:
        for word in words:
            if word.lower() in normalized:
                score = len(word) + (10 if business_line != "unknown" and metric.metric_id.startswith(business_line.split("_")[0]) else 0)
                candidates.append((score, metric))
                break
    if not candidates:
        return None
    metric = sorted(candidates, key=lambda item: item[0], reverse=True)[0][1]
    if business_line == "corporate" and metric.metric_id == "deposit_balance":
        return METRICS[0][0]
    if business_line == "retail" and metric.metric_id == "deposit_balance":
        return METRICS[1][0]
    if business_line == "corporate" and metric.metric_id in {"loan_balance", "customer_count"}:
        return METRICS[3][0] if metric.metric_id == "loan_balance" else METRICS[6][0]
    if business_line == "retail" and metric.metric_id in {"loan_balance", "customer_count"}:
        return METRICS[4][0] if metric.metric_id == "loan_balance" else METRICS[7][0]
    if business_line == "inclusive_finance" and metric.metric_id == "loan_balance":
        return METRICS[5][0]
    return metric


def _detect_dimensions(normalized: str) -> List[Dict[str, str]]:
    dimensions: List[Dict[str, str]] = []
    for dimension_id, name, words in DIMENSIONS:
        if any(word in normalized for word in words):
            dimensions.append({"dimension_id": dimension_id, "name": name, "role": "group_by"})
    return dimensions


def _parse_time(normalized: str, today: date) -> Tuple[Dict[str, Any], List[str]]:
    assumptions: List[str] = ["默认币种按人民币口径处理。"]
    month_range = re.search(r"(?:(\d{4})年)?(\d{1,2})[-至到](\d{1,2})月", normalized)
    if month_range:
        year = int(month_range.group(1) or today.year)
        start_month = int(month_range.group(2))
        end_month = int(month_range.group(3))
        start = date(year, start_month, 1)
        end = date(year, end_month, calendar.monthrange(year, end_month)[1])
        return _time_payload(start, end, "month", "余额" in normalized or "规模" in normalized), assumptions
    explicit_month = re.search(r"(?:(\d{4})年)?(\d{1,2})月", normalized)
    if explicit_month:
        year = int(explicit_month.group(1) or today.year)
        start_month = int(explicit_month.group(2))
        end_month = start_month
        start = date(year, start_month, 1)
        end = date(year, end_month, calendar.monthrange(year, end_month)[1])
        return _time_payload(start, end, "month", "余额" in normalized or "规模" in normalized), assumptions
    if "上月" in normalized:
        month_end = date(today.year, today.month, 1) - timedelta(days=1)
        start = date(month_end.year, month_end.month, 1)
        return _time_payload(start, month_end, "month", "余额" in normalized), assumptions
    if "今年" in normalized:
        return _time_payload(date(today.year, 1, 1), today, "year", False), assumptions
    if "去年" in normalized:
        return _time_payload(date(today.year - 1, 1, 1), date(today.year - 1, 12, 31), "year", False), assumptions
    prev_month_end = date(today.year, today.month, 1) - timedelta(days=1)
    prev_month_start = date(prev_month_end.year, prev_month_end.month, 1)
    assumptions.append("用户未指定时间，默认按最近已完结自然月处理。")
    return _time_payload(prev_month_start, prev_month_end, "month", "余额" in normalized or "规模" in normalized), assumptions


def _time_payload(start: date, end: date, grain: Optional[str], point_in_time: bool) -> Dict[str, Any]:
    return {
        "time_range": {"start": start.isoformat(), "end": end.isoformat(), "type": "natural_period"},
        "grain": grain,
        "point_in_time": point_in_time,
        "calendar_type": "natural",
    }


def _detect_intent_type(normalized: str) -> str:
    if any(word in normalized for word in ("同比", "环比", "较年初", "较上月末")):
        return "comparison"
    if any(word in normalized for word in ("排名", "排行", "top")):
        return "ranking"
    if any(word in normalized for word in ("趋势", "走势", "按月", "每月")):
        return "trend"
    if any(word in normalized for word in ("定义", "口径", "是什么意思", "含义")):
        return "definition"
    if any(word in normalized for word in ("明细", "详情", "逐笔")):
        return "detail"
    return "analysis"


def _build_comparison(normalized: str) -> Dict[str, Any]:
    if "同比" in normalized:
        return {"type": "year_over_year", "base_range": "prior_year_same_period", "calculation": "growth_rate"}
    if "环比" in normalized:
        return {"type": "period_over_period", "base_range": "previous_comparable_period", "calculation": "growth_rate"}
    if "较年初" in normalized:
        return {"type": "vs_period_start", "base_range": "year_start", "calculation": "delta"}
    if "较上月末" in normalized:
        return {"type": "vs_previous_month_end", "base_range": "previous_month_end", "calculation": "delta"}
    return {"type": None, "base_range": None, "calculation": None}


def _parse_limit(normalized: str) -> Optional[int]:
    match = re.search(r"(?:前|top)(\d+)", normalized)
    return int(match.group(1)) if match else None


def _collect_gaps(
    normalized: str,
    metric: Optional[MetricDef],
    business_line: str,
    dimensions: List[Dict[str, str]],
    limit: Optional[int],
) -> Tuple[List[str], List[str], List[Dict[str, Any]]]:
    missing: List[str] = []
    questions: List[str] = []
    ambiguities: List[Dict[str, Any]] = []
    if metric is None:
        missing.append("metric")
        questions.append("请问要看哪个指标？例如客户数、新增客户数、存款余额或贷款余额。")
        ambiguities.append({"slot": "metric", "candidates": ["customer_count", "new_customer_count", "deposit_balance", "loan_balance"]})
    elif metric.requires_business_line and business_line == "unknown":
        missing.append("business_line")
        questions.append("请问要看哪个业务线口径？例如对公、个人、普惠，还是全行汇总口径。")
        ambiguities.append({"slot": "business_line", "candidates": ["corporate", "retail", "inclusive_finance", "whole_bank"]})
    if ("排名" in normalized or "排行" in normalized) and not dimensions:
        missing.append("entity_dimension")
        questions.append("请问按哪个维度排名？例如机构、区域、渠道或产品。")
    if "客户排名" in normalized and metric is None:
        return missing, questions, ambiguities
    if ("规模" in normalized or "余额" in normalized) and metric is None:
        missing.append("product_scope")
    if ("排名" in normalized or "排行" in normalized) and limit is None:
        return missing, questions, ambiguities
    return missing, questions, ambiguities


def _build_sort(intent_type: str, metric: Optional[MetricDef]) -> List[Dict[str, str]]:
    if intent_type == "ranking" and metric:
        return [{"field": metric.metric_id, "direction": "desc"}]
    return []


def _metric_payload(metric: MetricDef) -> Dict[str, Any]:
    return {
        "metric_id": metric.metric_id,
        "name": metric.name,
        "aggregation": metric.aggregation,
        "formula": metric.formula,
        "unit": metric.unit,
    }


def _schema_hints(metric: Optional[MetricDef], dimensions: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    hints: List[Dict[str, Any]] = []
    if metric:
        hints.append({"canonical_id": metric.metric_id, "type": "metric", "candidate_tables": [], "candidate_columns": [], "join_keys": [], "notes": []})
    for item in dimensions[:3]:
        hints.append({"canonical_id": item["dimension_id"], "type": "dimension", "candidate_tables": [], "candidate_columns": [], "join_keys": [], "notes": []})
    return hints


def _infer_domain(normalized: str) -> str:
    for keyword, domain in (("存款", "deposit"), ("贷款", "loan"), ("客户", "customer"), ("理财", "wealth"), ("交易", "transaction")):
        if keyword in normalized:
            return domain
    return ""
