from __future__ import annotations

import re
from typing import Dict, Optional

_FIELD_LABELS: Dict[str, str] = {
    # sales_order schema
    "order_date": "订单日期",
    "region": "区域",
    "department": "部门",
    "product_category": "产品类别",
    "product_name": "产品名称",
    "channel": "渠道",
    "customer_type": "客户类型",
    "sales_amount": "销售额",
    "order_count": "订单数",
    "customer_count": "客户数",
    "gross_profit": "毛利",
    "target_amount": "目标销售额",
    # customer_profile schema
    "stat_month": "统计月份",
    "new_customers": "新增客户",
    "active_customers": "活跃客户",
    "retained_customers": "留存客户",
    "churned_customers": "流失客户",
    # common generic English names
    "amount": "金额",
    "balance": "余额",
    "principal": "本金",
    "principal_balance": "本金余额",
    "principal_balance_amt": "本金余额",
    "interest": "利息",
    "loan": "贷款",
    "loan_balance": "贷款余额",
    "loan_balance_amt": "贷款余额",
    "loan_type": "贷款类型",
    "loan_status": "贷款状态",
    "loan_risk_level": "贷款风险等级",
    "sales": "销售额",
    "revenue": "营收",
    "profit": "利润",
    "count": "数量",
    "total": "合计",
    "date": "日期",
    "month": "月份",
    "year": "年份",
    "name": "名称",
    "type": "类型",
    "category": "类别",
    "status": "状态",
    "branch": "支行",
    "employee_count": "员工数",
    "employees": "员工数",
    "customer": "客户",
    "product": "产品",
    "price": "单价",
    "qty": "数量",
    "quantity": "数量",
    "overdue": "逾期",
    "overdue_days": "逾期天数",
    "risk": "风险",
    "score": "评分",
    "ratio": "比率",
    "rate": "比率",
    "days": "天数",
}

_DOMAIN_LABELS: Dict[str, str] = {
    "loan_risk": "贷款风险",
    "customer": "客户经营",
    "marketing_roi": "营销投产",
    "generic_table": "通用业务表",
}

_TOKEN_LABELS: Dict[str, str] = {
    "amt": "金额",
    "amount": "金额",
    "avg": "平均",
    "balance": "余额",
    "branch": "支行",
    "cnt": "数量",
    "count": "数量",
    "customer": "客户",
    "date": "日期",
    "days": "天数",
    "dpd": "逾期天数",
    "exposure": "敞口",
    "id": "编号",
    "interest": "利息",
    "loan": "贷款",
    "loss": "损失",
    "max": "最大",
    "min": "最小",
    "month": "月份",
    "name": "名称",
    "npl": "不良贷款",
    "overdue": "逾期",
    "pd": "违约概率",
    "pct": "占比",
    "principal": "本金",
    "product": "产品",
    "ratio": "比率",
    "rate": "比率",
    "region": "区域",
    "risk": "风险",
    "score": "评分",
    "status": "状态",
    "sum": "合计",
    "total": "总量",
    "type": "类型",
    "year": "年份",
}


def field_display_name(field: str, column_labels: Optional[Dict[str, str]] = None) -> str:
    if not field:
        return field
    if column_labels and field in column_labels:
        return str(column_labels[field])
    if field in _FIELD_LABELS:
        return _FIELD_LABELS[field]
    for prefix in ("sum_", "count_", "avg_", "max_", "min_"):
        if field.startswith(prefix):
            inner = field[len(prefix) :]
            nested = field_display_name(inner, column_labels)
            return nested if nested != inner else _compose_label(field)
    return _compose_label(field)


def domain_display_name(domain: str) -> str:
    if not domain:
        return "通用业务表"
    if domain in _DOMAIN_LABELS:
        return _DOMAIN_LABELS[domain]
    return _compose_label(domain)


def _compose_label(raw: str) -> str:
    if re.search(r"[\u4e00-\u9fff]", raw):
        return raw.replace("_", " ")
    parts = [part for part in _split_identifier(raw) if part]
    translated = [
        _TOKEN_LABELS.get(part.lower(), part.upper() if part.isupper() else part) for part in parts
    ]
    return "".join(translated) if translated else raw.replace("_", " ")


def _split_identifier(raw: str) -> list[str]:
    normalized = raw.replace("-", "_")
    normalized = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", normalized)
    return [part for part in normalized.split("_") if part]
