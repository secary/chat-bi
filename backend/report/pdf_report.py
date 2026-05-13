"""Build PDF export from persisted session messages (HTML → WeasyPrint)."""

from __future__ import annotations

import base64
import html
import io
from datetime import datetime, timezone
from typing import Any, Dict, List

from backend.report.pdf_chart_png import echarts_option_to_png_bytes
from backend.report.pdf_summary import _markdown_to_html, summarize_session_for_pdf


def _chart_to_png_bytes(chart: Any) -> bytes | None:
    from backend.report.pdf_chart_png import echarts_option_to_png_bytes

    return echarts_option_to_png_bytes(chart)


def _kpi_table_row(card: Dict[str, Any]) -> str:
    label = html.escape(str(card.get("label") or ""))
    value = html.escape(str(card.get("value") or ""))
    unit = html.escape(str(card.get("unit") or ""))
    return f"<tr><td>{label}</td><td>{value}</td><td>{unit}</td></tr>"


def _collect_kpi_cards(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for msg in messages:
        if str(msg.get("role") or "") != "assistant":
            continue
        kpis = msg.get("kpiCards")
        if isinstance(kpis, list):
            for k in kpis:
                if isinstance(k, dict):
                    out.append(k)
    return out


def _chart_pngs(messages: List[Dict[str, Any]]) -> List[bytes]:
    pngs: List[bytes] = []
    for msg in messages:
        if str(msg.get("role") or "") != "assistant":
            continue
        chart = msg.get("chart")
        if chart is None:
            continue
        png = _chart_to_png_bytes(chart)
        if png:
            pngs.append(png)
    return pngs


def messages_to_html_document(messages: List[Dict[str, Any]], title: str) -> str:
    """精炼摘要 + KPI 汇总 + 图表 PNG（非全文复制对话）。"""
    safe_title = html.escape(title)
    summary = summarize_session_for_pdf(messages)
    summary_html = _markdown_to_html(summary)

    kpis = _collect_kpi_cards(messages)
    kpi_block = ""
    if kpis:
        rows = "".join(_kpi_table_row(k) for k in kpis)
        kpi_block = (
            '<h2 class="sec">关键指标</h2>'
            "<table class='kpi'><thead><tr><th>指标</th><th>数值</th><th>单位</th></tr></thead>"
            f"<tbody>{rows}</tbody></table>"
        )

    chart_sections: List[str] = []
    idx = 0
    for msg in messages:
        if str(msg.get("role") or "") != "assistant":
            continue
        chart = msg.get("chart")
        if chart is None:
            continue
        png = _chart_to_png_bytes(chart)
        idx += 1
        if not png:
            chart_sections.append(
                f'<p class="chart-note">图表 {idx}（无法导出为静态图，请在应用内查看）</p>'
            )
            continue
        b64 = base64.standard_b64encode(png).decode("ascii")
        chart_sections.append(
            f'<figure class="chart-wrap"><figcaption>图表 {idx}</figcaption>'
            f'<img class="chart-img" src="data:image/png;base64,{b64}" alt="chart {idx}"/></figure>'
        )

    charts_html = "\n".join(chart_sections)
    now = html.escape(datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"/>
<title>{safe_title}</title>
<style>
body {{ font-family: "Noto Sans CJK SC", "Microsoft YaHei", sans-serif; font-size: 11pt;
  margin: 24px; color: #222; }}
h1 {{ font-size: 16pt; margin-bottom: 8px; }}
h2.sec {{ font-size: 12pt; margin-top: 20px; margin-bottom: 8px; color: #374151; }}
.sub {{ color: #666; font-size: 9pt; margin-bottom: 16px; }}
.summary {{ line-height: 1.6; margin-bottom: 20px; padding: 12px; background: #f9fafb;
  border-radius: 8px; border: 1px solid #e5e7eb; }}
.kpi {{ border-collapse: collapse; width: 100%; margin-top: 8px; font-size: 10pt; }}
.kpi th, .kpi td {{ border: 1px solid #ddd; padding: 6px; text-align: left; }}
.chart-note {{ font-size: 9pt; color: #6b7280; }}
.chart-wrap {{ margin: 16px 0; text-align: center; }}
.chart-wrap figcaption {{ font-size: 9pt; color: #6b7280; margin-bottom: 6px; }}
.chart-img {{ max-width: 100%; height: auto; }}
</style>
</head>
<body>
<h1>{safe_title}</h1>
<p class="sub">导出时间 {now}</p>
<h2 class="sec">摘要</h2>
<div class="summary">{summary_html}</div>
{kpi_block}
<h2 class="sec">可视化图表</h2>
{charts_html if charts_html else '<p class="chart-note">本会话无可嵌入图表。</p>'}
</body>
</html>"""


def render_session_pdf_bytes(messages: List[Dict[str, Any]], session_title: str) -> bytes:
    """Return PDF bytes, fallback to ReportLab when WeasyPrint fails."""
    html_doc = messages_to_html_document(messages, session_title or "ChatBI 会话报告")
    try:
        from weasyprint import HTML

        return HTML(string=html_doc).write_pdf()
    except Exception:
        return _render_pdf_with_reportlab(messages, session_title or "ChatBI 会话报告")


def _render_pdf_with_reportlab(messages: List[Dict[str, Any]], session_title: str) -> bytes:
    try:
        from PIL import Image as PILImage
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        from reportlab.platypus import (
            Image,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
        from reportlab.lib import colors
    except Exception as exc:
        raise RuntimeError(
            "PDF 导出依赖加载失败：请安装 weasyprint 系统依赖，或确保 reportlab / pillow 可用。"
        ) from exc

    font_name = "STSong-Light"
    try:
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    except Exception:
        font_name = "Helvetica"

    summary = summarize_session_for_pdf(messages)
    summary_html = _markdown_to_html(summary)
    # Strip HTML tags for plain-text fallback in ReportLab
    import re

    plain_summary = re.sub(r"<[^>]+>", "", summary_html)
    pngs = _chart_pngs(messages)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )
    body_style = ParagraphStyle(
        name="Body",
        fontName=font_name,
        fontSize=10,
        leading=15,
    )
    h2_style = ParagraphStyle(
        name="H2",
        fontName=font_name,
        fontSize=13,
        leading=18,
        spaceBefore=14,
        spaceAfter=6,
    )
    h3_style = ParagraphStyle(
        name="H3",
        fontName=font_name,
        fontSize=11,
        leading=15,
        spaceBefore=10,
        spaceAfter=4,
    )
    li_style = ParagraphStyle(
        name="Li",
        fontName=font_name,
        fontSize=10,
        leading=14,
        leftIndent=16,
        bulletIndent=8,
    )
    title_style = ParagraphStyle(
        name="Title",
        fontName=font_name,
        fontSize=16,
        leading=20,
        spaceAfter=8,
    )
    caption_style = ParagraphStyle(
        name="Caption",
        fontName=font_name,
        fontSize=8,
        leading=10,
        textColor=colors.grey,
    )

    def _parse_summary_to_flowables(text: str) -> List[Any]:
        """Parse minimal HTML from _markdown_to_html into ReportLab flowables."""
        import re

        flowables: List[Any] = []
        # Split on HTML block tags
        parts = re.split(r"(?=<[uhlp][^>]*>)", text)
        for part in parts:
            part = part.strip()
            if not part:
                continue
            m = re.match(r"^<h([23])>(.+)</h\1>$", part)
            if m:
                level = int(m.group(1))
                content = re.sub(r"<[^>]+>", "", m.group(2))
                style = h2_style if level == 2 else h3_style
                flowables.append(Paragraph(content, style))
                continue
            m = re.match(r"^<p>(.*)</p>$", part)
            if m:
                content = m.group(1).replace("<strong>", "<b>").replace("</strong>", "</b>")
                content = re.sub(r"<[^>]+>", "", content)
                if content:
                    flowables.append(Paragraph(content, body_style))
                continue
            m = re.match(r"^<li>(.*)</li>$", part)
            if m:
                content = re.sub(r"<[^>]+>", "", m.group(1))
                flowables.append(Paragraph(f"• {content}", li_style))
                continue
            # fallback: strip tags
            clean = re.sub(r"<[^>]+>", "", part)
            if clean.strip():
                flowables.append(Paragraph(clean, body_style))
        return flowables

    story: List[Any] = []
    story.append(Paragraph(html.escape(session_title), title_style))
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    story.append(Paragraph(html.escape(f"导出时间: {ts}"), body_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph("摘要", h2_style))
    story.extend(_parse_summary_to_flowables(summary_html))
    story.append(Spacer(1, 10))

    kpis = _collect_kpi_cards(messages)
    if kpis:
        story.append(Paragraph("关键指标", h2_style))
        kpi_data = [["指标", "数值", "单位"]]
        for card in kpis:
            kpi_data.append(
                [
                    str(card.get("label", "")),
                    str(card.get("value", "")),
                    str(card.get("unit", "")),
                ]
            )
        kpi_table = Table(kpi_data, colWidths=[2.5 * inch, 1.8 * inch, 1.2 * inch])
        kpi_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("FONTNAME", (0, 0), (-1, 0), font_name),
                    ("FONTNAME", (0, 1), (-1, -1), font_name),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("PADDING", (0, 0), (-1, -1), 5),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        story.append(kpi_table)
        story.append(Spacer(1, 10))

    if pngs:
        story.append(Paragraph("可视化图表", h2_style))
        max_w = 6 * inch
        for i, png_bytes in enumerate(pngs, start=1):
            pil_img = PILImage.open(io.BytesIO(png_bytes))
            iw, ih = pil_img.size
            scale = min(1.0, max_w / float(iw))
            w = iw * scale
            h = ih * scale
            story.append(Paragraph(f"图表 {i}", body_style))
            story.append(Spacer(1, 4))
            story.append(Image(io.BytesIO(png_bytes), width=w, height=h))
            story.append(Spacer(1, 8))

    doc.build(story)
    return buffer.getvalue()
