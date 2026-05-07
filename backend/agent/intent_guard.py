from __future__ import annotations

import re

_BUSINESS_HINT_RE = re.compile(
    r"(销售|毛利|利润|营收|收入|趋势|环比|同比|排行|排名|图表|数据|分析|查询|客户|订单|区域|渠道|产品|指标|kpi)",
    re.IGNORECASE,
)
_SMALL_TALK_RE = re.compile(
    r"^(你好|您好|hi|hello|早上好|下午好|晚上好|谢谢|感谢|辛苦了|好的|ok|嗯|嗯嗯|在吗|收到)[!！,.。?？ ]*$",
    re.IGNORECASE,
)


def should_skip_skill_for_message(user_text: str) -> bool:
    """Return True when a message is plain social chatter."""
    text = (user_text or "").strip()
    if not text:
        return True
    if _BUSINESS_HINT_RE.search(text):
        return False
    if len(text) <= 12 and _SMALL_TALK_RE.match(text):
        return True
    return False


def small_talk_reply(user_text: str) -> str:
    text = (user_text or "").strip()
    if "谢谢" in text or "感谢" in text:
        return "不客气。我在，您可以继续问业务数据问题，比如“各区域销售额排行”或“4月毛利率环比”。"
    return "您好，我在。您可以直接说一个数据分析问题，我会按需调用技能并尽量减少不必要计算。"
