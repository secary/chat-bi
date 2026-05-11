"""Extract tabular data from chart/screenshot images via LiteLLM vision."""

from __future__ import annotations

import base64
import json
import mimetypes
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.llm_runtime import chatbi_acompletion
from backend.trace import log_event

_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}

_EXTRACT_PROMPT = """你是报表识读助手。请阅读图像中的表格或图表图例与数据标签，尽可能还原为结构化表格。
输出**仅**一个 JSON 对象，字段：
- columns: 字符串数组，表头
- rows: 数组，每项为对象，键与 columns 对齐；值为字符串或数字
- confidence: 0 到 1 之间浮点数
- notes: 简短中文说明识读限制或不确定点

若图像无法识别表格或图表数据，rows 用 []，notes 说明原因。"""


def find_image_path_in_text(text: str) -> Optional[Path]:
    """Locate first path to an allowed image file embedded in user text."""
    for m in re.finditer(r"[^\s]+\.(?:png|jpg|jpeg|webp)\b", text, flags=re.IGNORECASE):
        raw = m.group(0).strip("\"'`")
        p = Path(raw)
        if p.suffix.lower() in _IMAGE_SUFFIXES and p.is_file():
            return p
    for m in re.finditer(r"(/[^\s]+\.(?:png|jpg|jpeg|webp))", text, flags=re.IGNORECASE):
        p = Path(m.group(1))
        if p.suffix.lower() in _IMAGE_SUFFIXES and p.is_file():
            return p
    return None


def _truncate_rows(rows: List[Dict[str, Any]], max_rows: int) -> List[Dict[str, Any]]:
    if len(rows) <= max_rows:
        return rows
    return rows[:max_rows]


def _coerce_payload(raw: Dict[str, Any], max_rows: int) -> Dict[str, Any]:
    cols = raw.get("columns")
    rows = raw.get("rows")
    out_c: List[str] = []
    if isinstance(cols, list):
        out_c = [str(c) for c in cols if c is not None]
    out_r: List[Dict[str, Any]] = []
    if isinstance(rows, list):
        for item in rows:
            if isinstance(item, dict):
                out_r.append({str(k): item[k] for k in item})
    conf = raw.get("confidence")
    try:
        cf = float(conf) if conf is not None else 0.5
    except (TypeError, ValueError):
        cf = 0.5
    cf = max(0.0, min(1.0, cf))
    notes = raw.get("notes")
    ns = str(notes) if notes is not None else ""
    out_r = _truncate_rows(out_r, max_rows)
    return {
        "columns": out_c,
        "rows": out_r,
        "confidence": cf,
        "notes": ns[:500],
    }


async def extract_chart_table_from_image(
    image_path: Path,
    trace_id: str = "",
) -> Dict[str, Any]:
    """Return normalized dict with columns, rows, confidence, notes."""
    max_rows = max(1, int(os.getenv("CHATBI_VISION_MAX_ROWS", "80")))
    if not image_path.is_file():
        return {
            "columns": [],
            "rows": [],
            "confidence": 0.0,
            "notes": "文件不存在或不可读",
        }
    mime = mimetypes.guess_type(str(image_path))[0] or "image/png"
    b64 = base64.standard_b64encode(image_path.read_bytes()).decode("ascii")
    data_url = f"data:{mime};base64,{b64}"
    messages = [
        {"role": "system", "content": _EXTRACT_PROMPT},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "请抽取图中表格或图表数据。"},
                {"type": "image_url", "image_url": {"url": data_url}},
            ],
        },
    ]
    try:
        resp = await chatbi_acompletion(
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.1,
        )
    except Exception as exc:
        log_event(
            trace_id,
            "vision.extract",
            "failed",
            str(exc),
            level="WARN",
        )
        return {
            "columns": [],
            "rows": [],
            "confidence": 0.0,
            "notes": f"模型调用失败：{exc}",
        }
    content = resp.choices[0].message.content
    if not content:
        return {
            "columns": [],
            "rows": [],
            "confidence": 0.0,
            "notes": "模型无输出",
        }
    try:
        raw = json.loads(content.strip())
    except json.JSONDecodeError:
        return {
            "columns": [],
            "rows": [],
            "confidence": 0.0,
            "notes": "解析 JSON 失败",
        }
    if not isinstance(raw, dict):
        return {
            "columns": [],
            "rows": [],
            "confidence": 0.0,
            "notes": "模型输出格式异常",
        }
    result = _coerce_payload(raw, max_rows)
    log_event(
        trace_id,
        "vision.extract",
        "ok",
        payload={
            "rows": len(result["rows"]),
            "confidence": result["confidence"],
        },
    )
    return result


async def enrich_last_user_message_with_vision(
    messages: List[Dict[str, str]],
    trace_id: str = "",
) -> List[Dict[str, str]]:
    """If last message references an image upload, append vision JSON block."""
    if os.getenv("CHATBI_VISION_DISABLED", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    ):
        return messages
    if not messages:
        return messages
    last = messages[-1]
    if last.get("role") != "user":
        return messages
    content = str(last.get("content") or "")
    img = find_image_path_in_text(content)
    if img is None:
        return messages
    data = await extract_chart_table_from_image(img, trace_id=trace_id)
    blob = json.dumps(data, ensure_ascii=False)
    injected = (
        f"\n\n【图像结构化抽取】以下为模型从上传图像还原的表格 JSON（置信度 "
        f"{data.get('confidence', 0):.2f}），仅供参考：\n{blob}"
    )
    out = [dict(m) for m in messages[:-1]]
    out.append({"role": "user", "content": content + injected})
    return out
