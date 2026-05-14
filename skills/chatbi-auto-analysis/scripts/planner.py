from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Sequence

from formula_executor import formula_fields, group_fields
from utils import first


def propose_metrics(question: str, profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    llm_plans = propose_metrics_with_llm(question, profile)
    if llm_plans:
        return llm_plans
    return fallback_metric_plans(profile)


def propose_metrics_with_llm(question: str, profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    if os.getenv("CHATBI_AUTO_ANALYSIS_DISABLE_LLM", "0").lower() in {"1", "true", "yes"}:
        return []
    try:
        from backend.llm_runtime import chatbi_completion

        resp = chatbi_completion(
            messages=[
                {"role": "system", "content": AUTO_ANALYSIS_PLANNER_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps(
                        {"question": question, "table_profile": profile},
                        ensure_ascii=False,
                    ),
                },
            ],
            temperature=0.1,
            timeout=8,
        )
        payload = extract_json(completion_content(resp))
        plans = payload.get("metric_plans") if isinstance(payload, dict) else None
        return [item for item in plans or [] if isinstance(item, dict)]
    except Exception:
        return []


def fallback_metric_plans(profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    time_field = first(profile.get("time_columns", []))
    numeric = first(profile.get("numeric_columns", []))
    category = first(profile.get("categorical_columns", []))
    proposals: List[Dict[str, Any]] = []
    if time_field and numeric:
        proposals.append(
            metric(
                "metric_trend",
                f"{numeric}趋势",
                f"sum({numeric})",
                "line",
                [{"field": time_field, "transform": "month", "alias": "月份"}],
                {"op": "sum", "field": numeric},
                0.62,
            )
        )
    if category and numeric:
        proposals.append(
            metric(
                "category_breakdown",
                f"{numeric}结构拆解",
                f"sum({numeric})",
                "bar",
                [{"field": category, "alias": category}],
                {"op": "sum", "field": numeric},
                0.6,
            )
        )
    return proposals[:5]


def metric(
    metric_id: str,
    name: str,
    formula_text: str,
    chart_type: str,
    group_by: Sequence[Dict[str, str]],
    formula: Dict[str, Any],
    confidence: float,
) -> Dict[str, Any]:
    return {
        "id": metric_id,
        "name": name,
        "description": f"基于已识别字段自动建议分析「{name}」。",
        "formula_md": f"`{formula_text}`",
        "group_by": list(group_by),
        "formula": formula,
        "matched_fields": sorted(formula_fields(formula) | group_fields(group_by)),
        "chart_hint": chart_type,
        "confidence": confidence,
        "selected": confidence >= 0.7,
    }


def extract_json(text: str) -> Dict[str, Any]:
    try:
        loaded = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end <= start:
            return {}
        try:
            loaded = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return {}
    return loaded if isinstance(loaded, dict) else {}


def completion_content(resp: Any) -> str:
    try:
        return str(resp.choices[0].message.content or "")
    except Exception:
        return ""


AUTO_ANALYSIS_PLANNER_PROMPT = """
你是 ChatBI 上传表自动分析规划器。你只能输出 JSON，不要 Markdown。

任务：根据用户问题和 table_profile，推荐 1-5 个可分析指标。你只负责生成受控分析计划，不计算数值。

输出格式：
{
  "metric_plans": [
    {
      "id": "short_snake_case",
      "name": "指标中文名",
      "description": "为什么建议分析这个指标",
      "formula_md": "`可读公式`",
      "group_by": [{"field": "真实字段名", "transform": "month|none", "alias": "展示维度名"}],
      "formula": {"op": "sum|count|count_distinct|subtract|ratio_percent", "...": "..."},
      "chart_hint": "line|bar|pie",
      "confidence": 0.0,
      "selected": true
    }
  ]
}

公式 DSL 白名单：
- {"op":"sum","field":"字段名","filter": 可选过滤}
- {"op":"count","filter": 可选过滤}
- {"op":"count_distinct","field":"字段名","filter": 可选过滤}
- {"op":"subtract","left":公式,"right":公式}
- {"op":"ratio_percent","numerator":公式,"denominator":公式}

过滤 DSL 白名单：
- {"field":"字段名","op":"contains|eq|gt|gte|lt|lte","value":值}
- {"any":[过滤...]}
- {"all":[过滤...]}

约束：
- 只能引用 table_profile.columns 中真实存在的字段名。
- 如果字段口径不够明确，少推荐或不给推荐，不要臆造字段。
- group_by.transform 只有时间字段需要 month，其余可省略或写 none。
""".strip()
