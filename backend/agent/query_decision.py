from __future__ import annotations

import re


DECISION_RE = re.compile(r"(决策建议|决策意见|经营建议|经营意见|管理建议|管理意见|建议|意见)")
QUERY_RE = re.compile(
    r"(排行|排名|对比|趋势|汇总|查询|销售额|毛利|毛利率|目标完成率|留存率|客户数|订单数|"
    r"各区域|按区域|按月|按照.{0,10}划分|按.{0,10}划分|产品|渠道|部门|客户类型)"
)


def is_query_plus_decision_text(text: str) -> bool:
    return bool(text and QUERY_RE.search(text) and DECISION_RE.search(text))
