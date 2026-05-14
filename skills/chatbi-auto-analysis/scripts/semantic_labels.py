from __future__ import annotations

import contextlib
import io
import json
import os
from typing import Any, Dict, Optional


def infer_display_semantics(
    question: str,
    profile: Dict[str, Any],
    column_labels: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    if os.getenv("CHATBI_AUTO_ANALYSIS_DISABLE_LLM", "0").lower() in {"1", "true", "yes"}:
        return {}
    try:
        from backend.llm_runtime import chatbi_completion

        _buf = io.StringIO()
        with contextlib.redirect_stdout(_buf):
            resp = chatbi_completion(
                messages=[
                    {"role": "system", "content": DISPLAY_SEMANTICS_PROMPT},
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "question": question,
                                "known_column_labels": column_labels or {},
                                "table_profile": {
                                    "row_count": profile.get("row_count", 0),
                                    "domain_guess": profile.get("domain_guess", ""),
                                    "columns": [
                                        {
                                            "name": item.get("name"),
                                            "dtype": item.get("dtype"),
                                            "semantic_role": item.get("semantic_role"),
                                            "sample_values": item.get("sample_values", [])[:3],
                                        }
                                        for item in profile.get("columns", [])
                                        if isinstance(item, dict)
                                    ],
                                },
                            },
                            ensure_ascii=False,
                        ),
                    },
                ],
                temperature=0.1,
                timeout=6,
            )
        return _normalize_payload(_completion_content(resp), profile)
    except Exception:
        return {}


def _normalize_payload(text: str, profile: Dict[str, Any]) -> Dict[str, Any]:
    payload = _extract_json(text)
    if not isinstance(payload, dict):
        return {}
    field_names = {
        str(item.get("name"))
        for item in profile.get("columns", [])
        if isinstance(item, dict) and item.get("name")
    }
    raw_labels = payload.get("field_labels")
    field_labels: Dict[str, str] = {}
    if isinstance(raw_labels, dict):
        for key, value in raw_labels.items():
            if key in field_names and isinstance(value, str) and value.strip():
                field_labels[str(key)] = value.strip()
    domain_label = payload.get("domain_label")
    out: Dict[str, Any] = {}
    if isinstance(domain_label, str) and domain_label.strip():
        out["domain_label"] = domain_label.strip()
    if field_labels:
        out["field_labels"] = field_labels
    return out


def _extract_json(text: str) -> Dict[str, Any]:
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


def _completion_content(resp: Any) -> str:
    try:
        return str(resp.choices[0].message.content or "")
    except Exception:
        return ""


DISPLAY_SEMANTICS_PROMPT = """
你是 ChatBI 上传表字段展示名语义推断器。你只能输出 JSON，不要 Markdown。

任务：
1. 基于用户问题、字段名、字段角色、样例值，给出适合前端展示的中文字段名。
2. 给出一句简短的中文领域标签，用于展示“这张表主要是什么业务”。

输出格式：
{
  "domain_label": "中文领域名",
  "field_labels": {
    "真实字段名": "中文展示名"
  }
}

约束：
- 只能为 table_profile.columns 中真实存在的字段生成 field_labels。
- 优先做语义理解，不要逐词硬翻；比如 investment_amount 可以归纳成“投资金额”。
- 展示名要短、自然、适合业务用户阅读，避免英文夹杂。
- 如果 known_column_labels 已经给出标准中文名，不要改写它们。
- 不确定时可以少填，不要臆造复杂业务口径。
""".strip()
