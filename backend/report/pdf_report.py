"""Build PDF export from persisted session messages (HTML → WeasyPrint)."""

from __future__ import annotations

import html
from datetime import datetime, timezone
from typing import Any, Dict, List


def _kpi_table_row(card: Dict[str, Any]) -> str:
    label = html.escape(str(card.get("label") or ""))
    value = html.escape(str(card.get("value") or ""))
    unit = html.escape(str(card.get("unit") or ""))
    return f"<tr><td>{label}</td><td>{value}</td><td>{unit}</td></tr>"


def messages_to_html_document(messages: List[Dict[str, Any]], title: str) -> str:
    sections: List[str] = []
    safe_title = html.escape(title)
    for msg in messages:
        role = str(msg.get("role") or "")
        content = html.escape(str(msg.get("content") or "")).replace("\n", "<br/>")
        cls = "user" if role == "user" else "assistant"
        label = "用户" if role == "user" else "助手"
        block = [
            f'<section class="bubble {cls}">',
            f'<div class="meta">{label}</div>',
            f'<div class="body">{content}</div>',
        ]
        if role == "assistant":
            thinking = msg.get("thinking")
            if isinstance(thinking, list) and thinking:
                items = "".join(
                    f"<li>{html.escape(str(t))}</li>" for t in thinking if str(t).strip()
                )
                block.append(f"<details><summary>思考步骤</summary><ul>{items}</ul></details>")
            kpis = msg.get("kpiCards")
            if isinstance(kpis, list) and kpis:
                rows = "".join(_kpi_table_row(k) for k in kpis if isinstance(k, dict))
                block.append(
                    "<table class='kpi'><thead><tr><th>指标</th><th>数值</th><th>单位</th></tr></thead>"
                    f"<tbody>{rows}</tbody></table>"
                )
            if msg.get("chart") is not None:
                block.append(
                    "<p class=\"chart-note\">（本回合包含图表，详见应用内交互视图）</p>"
                )
            err = msg.get("error")
            if err:
                block.append(f'<p class="err">{html.escape(str(err))}</p>')
        block.append("</section>")
        sections.append("\n".join(block))

    body = "\n".join(sections)
    now = html.escape(
        datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    )
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"/>
<title>{safe_title}</title>
<style>
body {{ font-family: "Noto Sans CJK SC", "Microsoft YaHei", sans-serif; font-size: 11pt;
  margin: 24px; color: #222; }}
h1 {{ font-size: 16pt; margin-bottom: 8px; }}
.sub {{ color: #666; font-size: 9pt; margin-bottom: 24px; }}
.bubble {{ margin-bottom: 16px; padding: 12px; border-radius: 8px; }}
.user {{ background: #eef6ff; border: 1px solid #cfe8ff; }}
.assistant {{ background: #f9fafb; border: 1px solid #e5e7eb; }}
.meta {{ font-weight: 600; margin-bottom: 6px; font-size: 10pt; color: #374151; }}
.body {{ line-height: 1.5; }}
details {{ margin-top: 8px; font-size: 10pt; }}
.kpi {{ border-collapse: collapse; width: 100%; margin-top: 8px; font-size: 10pt; }}
.kpi th, .kpi td {{ border: 1px solid #ddd; padding: 6px; text-align: left; }}
.chart-note {{ font-size: 9pt; color: #6b7280; }}
.err {{ color: #b91c1c; font-size: 10pt; }}
</style>
</head>
<body>
<h1>{safe_title}</h1>
<p class="sub">导出时间 {now}</p>
{body}
</body>
</html>"""


def render_session_pdf_bytes(messages: List[Dict[str, Any]], session_title: str) -> bytes:
    """Return PDF bytes (requires WeasyPrint system libraries)."""
    try:
        from weasyprint import HTML
    except OSError as exc:
        raise RuntimeError(
            "WeasyPrint 无法加载本地图形库，请在服务器镜像中安装 Pango/Cairo 依赖。"
        ) from exc
    html_doc = messages_to_html_document(messages, session_title or "ChatBI 会话报告")
    return HTML(string=html_doc).write_pdf()
