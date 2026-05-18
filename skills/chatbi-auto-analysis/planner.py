from __future__ import annotations

import contextlib
import io
import json
import os
from typing import Any, Dict, List, Optional, Sequence

from display_names import field_display_name
from formula_executor import formula_fields, group_fields
from utils import first


def _field_display_name(field: str, column_labels: Optional[Dict[str, str]] = None) -> str:
    return field_display_name(field, column_labels)


def propose_metrics(
    question: str,
    profile: Dict[str, Any],
    column_labels: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    analysis_hints = build_analysis_hints(profile, column_labels=column_labels)
    llm_plans = propose_metrics_with_llm(
        question,
        profile,
        column_labels=column_labels,
        analysis_hints=analysis_hints,
    )
    fallback_plans = fallback_metric_plans(profile, column_labels=column_labels)
    return merge_metric_plans(llm_plans, fallback_plans)


def propose_metrics_with_llm(
    question: str,
    profile: Dict[str, Any],
    column_labels: Optional[Dict[str, str]] = None,
    analysis_hints: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    if os.getenv("CHATBI_AUTO_ANALYSIS_DISABLE_LLM", "0").lower() in {"1", "true", "yes"}:
        return []
    try:
        from backend.llm_runtime import chatbi_completion

        _buf = io.StringIO()
        with contextlib.redirect_stdout(_buf):
            resp = chatbi_completion(
                messages=[
                    {"role": "system", "content": AUTO_ANALYSIS_PLANNER_PROMPT},
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "question": question,
                                "table_profile": profile,
                                "known_column_labels": column_labels or {},
                                "analysis_hints": analysis_hints or {},
                            },
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


def build_analysis_hints(
    profile: Dict[str, Any],
    column_labels: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    columns = [item for item in profile.get("columns", []) if isinstance(item, dict)]
    time_fields = [str(item) for item in profile.get("time_columns", []) if item][:2]
    numeric_fields = [str(item) for item in profile.get("numeric_columns", []) if item][:3]
    category_fields = [str(item) for item in profile.get("categorical_columns", []) if item][:4]
    id_fields = [str(item) for item in profile.get("id_columns", []) if item][:2]
    funnel_stages = detect_funnel_stages(profile, column_labels=column_labels)
    status_fields = [
        str(item.get("name"))
        for item in columns
        if item.get("semantic_role") == "status" and item.get("name")
    ][:2]
    hints: List[Dict[str, Any]] = []

    for field in numeric_fields:
        hints.append(
            {
                "method": "规模趋势",
                "metric_name_hint": f"{_field_display_name(field, column_labels)}趋势",
                "why": "存在时间字段和数值字段，适合做时间趋势。",
                "fields": {"measure": field, "time": time_fields[0] if time_fields else ""},
            }
        )
    for field in numeric_fields:
        for category in category_fields[:2]:
            hints.append(
                {
                    "method": "结构拆解",
                    "metric_name_hint": f"{_field_display_name(field, column_labels)}按{_field_display_name(category, column_labels)}分布",
                    "why": "存在类别字段和数值字段，适合看构成与集中度。",
                    "fields": {"measure": field, "category": category},
                }
            )
    if status_fields:
        for status in status_fields:
            hints.append(
                {
                    "method": "状态分布",
                    "metric_name_hint": f"{_field_display_name(status, column_labels)}分布",
                    "why": "存在状态字段，适合比较不同状态的记录数或金额。",
                    "fields": {
                        "status": status,
                        "measure": numeric_fields[0] if numeric_fields else "",
                    },
                }
            )
    if id_fields:
        for entity in id_fields:
            hints.append(
                {
                    "method": "主体数量",
                    "metric_name_hint": f"{_field_display_name(entity, column_labels)}数量",
                    "why": "存在 ID 字段，适合看主体数、去重数和覆盖范围。",
                    "fields": {"entity_id": entity, "time": time_fields[0] if time_fields else ""},
                }
            )
    if numeric_fields:
        for field in numeric_fields[:2]:
            hints.append(
                {
                    "method": "平均水平",
                    "metric_name_hint": f"平均{_field_display_name(field, column_labels)}",
                    "why": "存在数值字段，适合看均值与单笔水平。",
                    "fields": {
                        "measure": field,
                        "entity_id": id_fields[0] if id_fields else "",
                        "category": category_fields[0] if category_fields else "",
                    },
                }
            )
    if len(funnel_stages) >= 3:
        hints.append(
            {
                "method": "阶段漏斗",
                "metric_name_hint": "转化漏斗",
                "why": "存在多个具有前后业务阶段关系的数量字段，适合先汇总成总漏斗查看阶段衰减。",
                "fields": {"stages": [item["field"] for item in funnel_stages[:6]]},
            }
        )
    return {
        "domain_guess": profile.get("domain_guess", ""),
        "row_count": profile.get("row_count", 0),
        "time_fields": time_fields,
        "numeric_fields": numeric_fields,
        "category_fields": category_fields,
        "id_fields": id_fields,
        "status_fields": status_fields,
        "funnel_stages": funnel_stages[:6],
        "recommended_methods": hints[:10],
    }


def fallback_metric_plans(
    profile: Dict[str, Any],
    column_labels: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    def label(field: str) -> str:
        return _field_display_name(field, column_labels)

    time_fields = [str(item) for item in profile.get("time_columns", []) if item][:2]
    numeric_fields = [str(item) for item in profile.get("numeric_columns", []) if item][:3]
    category_fields = [str(item) for item in profile.get("categorical_columns", []) if item][:4]
    id_fields = [str(item) for item in profile.get("id_columns", []) if item][:2]
    funnel_stages = detect_funnel_stages(profile, column_labels=column_labels)
    status_fields = [
        str(item.get("name"))
        for item in profile.get("columns", [])
        if isinstance(item, dict) and item.get("semantic_role") == "status" and item.get("name")
    ][:2]
    proposals: List[Dict[str, Any]] = []

    if len(funnel_stages) >= 3:
        proposals.append(
            metric(
                "overall_conversion_funnel",
                "转化漏斗",
                "funnel(" + " -> ".join(item["field"] for item in funnel_stages[:6]) + ")",
                "funnel",
                [],
                {
                    "op": "funnel",
                    "stage_dimension": "阶段",
                    "stages": [
                        {
                            "label": item["label"],
                            "formula": {"op": "sum", "field": item["field"]},
                        }
                        for item in funnel_stages[:6]
                    ],
                },
                0.72,
            )
        )

    for time_field in time_fields[:1]:
        for numeric in numeric_fields[:2]:
            num_label = label(numeric)
            proposals.append(
                metric(
                    f"{numeric}_trend",
                    f"{num_label}趋势",
                    f"sum({numeric})",
                    "line",
                    [{"field": time_field, "transform": "month", "alias": label(time_field)}],
                    {"op": "sum", "field": numeric},
                    0.62,
                )
            )

    for category in category_fields[:3]:
        for numeric in numeric_fields[:2]:
            num_label = label(numeric)
            proposals.append(
                metric(
                    f"{numeric}_by_{category}",
                    f"{num_label}按{label(category)}分布",
                    f"sum({numeric})",
                    "pie",
                    [{"field": category, "alias": label(category)}],
                    {"op": "sum", "field": numeric},
                    0.6,
                )
            )

    for status in status_fields:
        proposals.append(
            metric(
                f"count_by_{status}",
                f"{label(status)}分布",
                "count()",
                "pie",
                [{"field": status, "alias": label(status)}],
                {"op": "count"},
                0.58,
            )
        )
        if numeric_fields:
            numeric = numeric_fields[0]
            proposals.append(
                metric(
                    f"{numeric}_by_{status}",
                    f"{label(status)}{label(numeric)}分布",
                    f"sum({numeric})",
                    "bar",
                    [{"field": status, "alias": label(status)}],
                    {"op": "sum", "field": numeric},
                    0.57,
                )
            )

    for entity in id_fields[:1]:
        if time_fields:
            time_field = time_fields[0]
            proposals.append(
                metric(
                    f"distinct_{entity}_trend",
                    f"{label(entity)}数量趋势",
                    f"count_distinct({entity})",
                    "line",
                    [{"field": time_field, "transform": "month", "alias": label(time_field)}],
                    {"op": "count_distinct", "field": entity},
                    0.59,
                )
            )
        if category_fields:
            category = category_fields[0]
            proposals.append(
                metric(
                    f"distinct_{entity}_by_{category}",
                    f"{label(entity)}数量结构",
                    f"count_distinct({entity})",
                    "bar",
                    [{"field": category, "alias": label(category)}],
                    {"op": "count_distinct", "field": entity},
                    0.57,
                )
            )

    if numeric_fields:
        base_numeric = numeric_fields[0]
        grouping_field = first(category_fields) or first(status_fields)
        if grouping_field:
            proposals.append(
                metric(
                    f"avg_{base_numeric}_by_{grouping_field}",
                    f"平均{label(base_numeric)}",
                    f"sum({base_numeric}) / count()",
                    "bar",
                    [{"field": grouping_field, "alias": label(grouping_field)}],
                    {
                        "op": "divide",
                        "numerator": {"op": "sum", "field": base_numeric},
                        "denominator": {"op": "count"},
                    },
                    0.55,
                )
            )

    return dedupe_metric_plans(proposals)[:10]


def merge_metric_plans(
    primary: Sequence[Dict[str, Any]], secondary: Sequence[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    merged = dedupe_metric_plans([*primary, *secondary])
    return merged[:10]


def dedupe_metric_plans(plans: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    out: List[Dict[str, Any]] = []
    for plan in plans:
        plan_id = str(plan.get("id") or "")
        name = str(plan.get("name") or "")
        key = (plan_id, name)
        if key in seen:
            continue
        seen.add(key)
        out.append(plan)
    return out


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


def detect_funnel_stages(
    profile: Dict[str, Any],
    column_labels: Optional[Dict[str, str]] = None,
) -> List[Dict[str, str]]:
    numeric_fields = [str(item) for item in profile.get("numeric_columns", []) if item]
    stages = []
    for field in numeric_fields:
        if not looks_like_stage_volume_field(field):
            continue
        stage_rank = funnel_stage_rank(field)
        if stage_rank is None:
            continue
        stages.append(
            {
                "field": field,
                "label": funnel_stage_label(field, column_labels=column_labels),
                "rank": stage_rank,
            }
        )
    ordered = sorted(stages, key=lambda item: int(item["rank"]))
    return [
        {"field": item["field"], "label": item["label"]} for item in ordered if item["rank"] <= 3
    ]


def funnel_stage_rank(field: str) -> Optional[int]:
    normalized = field.lower()
    rank_keywords = [
        (1, ["qualified", "mql", "sql", "intent", "有效", "意向", "合格"]),
        (0, ["lead", "clue", "visitor", "visit", "prospect", "线索", "获客"]),
        (2, ["proposal", "quote", "offer", "opportunity", "方案", "报价", "商机"]),
        (3, ["won", "win", "closed_won", "成交", "签约", "放款"]),
        (4, ["lost", "drop", "流失", "失败", "拒绝", "未成交"]),
    ]
    for rank, keywords in rank_keywords:
        if any(keyword in normalized for keyword in keywords):
            return rank
    return None


def funnel_stage_label(
    field: str,
    column_labels: Optional[Dict[str, str]] = None,
) -> str:
    normalized = field.lower()
    if any(
        keyword in normalized
        for keyword in ["qualified", "mql", "sql", "intent", "有效", "意向", "合格"]
    ):
        return "有效线索"
    if any(keyword in normalized for keyword in ["lead", "clue", "prospect", "线索", "获客"]):
        return "线索"
    if any(
        keyword in normalized
        for keyword in ["proposal", "quote", "offer", "opportunity", "方案", "报价", "商机"]
    ):
        return "方案/商机"
    if any(
        keyword in normalized for keyword in ["won", "win", "closed_won", "成交", "签约", "放款"]
    ):
        return "成交"
    if any(keyword in normalized for keyword in ["lost", "drop", "流失", "失败", "拒绝", "未成交"]):
        return "流失"
    return _field_display_name(field, column_labels)


def looks_like_stage_volume_field(field: str) -> bool:
    normalized = field.lower()
    if any(
        token in normalized
        for token in ["avg", "mean", "rate", "ratio", "amount", "amt", "size", "days"]
    ):
        return False
    return any(
        token in normalized
        for token in ["count", "cnt", "qty", "num", "volume", "数量", "户数", "笔数"]
    )


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

任务：根据用户问题和 table_profile，推荐 3-8 个可分析指标。你只负责生成受控分析计划，不计算数值。

输入里还会给你：
- known_column_labels：已有中文展示名
- analysis_hints：基于表结构预提炼出的可用分析方法

输出格式：
{
  "metric_plans": [
    {
      "id": "short_snake_case",
      "name": "指标中文名",
      "description": "为什么建议分析这个指标",
      "formula_md": "`可读公式`",
      "group_by": [{"field": "真实字段名", "transform": "month|none", "alias": "展示维度名"}],
      "formula": {"op": "sum|count|count_distinct|subtract|ratio_percent|funnel", "...": "..."},
      "chart_hint": "line|bar|pie|funnel|horizontal_bar|grouped_bar|stacked_bar|area|scatter|heatmap",
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
- {"op":"funnel","stage_dimension":"阶段","stages":[{"label":"阶段名","formula":公式}]}

过滤 DSL 白名单：
- {"field":"字段名","op":"contains|eq|gt|gte|lt|lte","value":值}
- {"any":[过滤...]}
- {"all":[过滤...]}

约束：
- 只能引用 table_profile.columns 中真实存在的字段名。
- 优先覆盖互补分析方法，而不是重复同一种图形：优先从趋势、结构拆解、状态分布、主体数量、平均水平、效率/占比中选择。
- 尽量使用 analysis_hints 里给出的分析机会，但可以按语义理解重命名或筛选。
- 如果字段口径不够明确，可以跳过该方法，但不要把结果收缩到只剩 1-2 个基础指标。
- group_by.transform 只有时间字段需要 month，其余可省略或写 none。
""".strip()
