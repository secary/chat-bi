from __future__ import annotations

import html
import json
from typing import Dict, Sequence

from .models import SemanticPlan


def numeric_value(value: object) -> float:
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return 0.0


def infer_chart_type(rows: Sequence[Dict[str, str]], dimension_columns: Sequence[str]) -> str:
    if not rows or not dimension_columns:
        return "table"
    if any(column == "月份" for column in dimension_columns):
        return "line"
    return "bar"


def build_chart_points(
    rows: Sequence[Dict[str, str]],
) -> tuple[list[str], list[float], str, list[str]]:
    if not rows:
        return [], [], "指标", []
    columns = list(rows[0].keys())
    metric_column = columns[-1]
    dimension_columns = columns[:-1]
    labels = []
    values = []
    for row in rows:
        label_parts = [str(row.get(column, "")) for column in dimension_columns]
        labels.append(" / ".join(part for part in label_parts if part) or metric_column)
        values.append(numeric_value(row.get(metric_column)))
    return labels, values, metric_column, dimension_columns


def render_svg_chart(title: str, rows: Sequence[Dict[str, str]], chart_type: str) -> str:
    labels, values, metric_column, _ = build_chart_points(rows)
    if not labels:
        return '<p class="empty">没有可绘制的数据</p>'

    width = 960
    height = 460
    left = 72
    right = 32
    top = 48
    bottom = 104
    plot_width = width - left - right
    plot_height = height - top - bottom
    max_value = max(values) if values else 1
    max_value = max_value if max_value > 0 else 1

    def x_at(index: int) -> float:
        if len(labels) == 1:
            return left + plot_width / 2
        return left + (plot_width * index / (len(labels) - 1))

    def y_at(value: float) -> float:
        return top + plot_height - (value / max_value * plot_height)

    parts = [
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(title)}">',
        f'<text x="{left}" y="28" class="title">{html.escape(title)}</text>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_height}" class="axis" />',
        f'<line x1="{left}" y1="{top + plot_height}" x2="{left + plot_width}" y2="{top + plot_height}" class="axis" />',
    ]

    for step in range(5):
        value = max_value * step / 4
        y = y_at(value)
        parts.append(
            f'<line x1="{left}" y1="{y:.2f}" x2="{left + plot_width}" y2="{y:.2f}" class="grid" />'
        )
        parts.append(
            f'<text x="{left - 10}" y="{y + 4:.2f}" text-anchor="end" class="tick">{value:.0f}</text>'
        )

    if chart_type == "line":
        points = " ".join(
            f"{x_at(index):.2f},{y_at(value):.2f}" for index, value in enumerate(values)
        )
        parts.append(f'<polyline points="{points}" class="line" />')
        for index, value in enumerate(values):
            x = x_at(index)
            y = y_at(value)
            parts.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="5" class="point" />')
            parts.append(
                f'<text x="{x:.2f}" y="{y - 10:.2f}" text-anchor="middle" class="value">{value:.0f}</text>'
            )
    else:
        gap = 16
        bar_width = max(16, (plot_width - gap * (len(labels) + 1)) / max(1, len(labels)))
        for index, value in enumerate(values):
            x = left + gap + index * (bar_width + gap)
            y = y_at(value)
            bar_height = top + plot_height - y
            parts.append(
                f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_width:.2f}" height="{bar_height:.2f}" class="bar" />'
            )
            parts.append(
                f'<text x="{x + bar_width / 2:.2f}" y="{y - 8:.2f}" text-anchor="middle" class="value">{value:.0f}</text>'
            )

    for index, label in enumerate(labels):
        x = (
            x_at(index)
            if chart_type == "line"
            else left + 16 + index * ((plot_width - 16) / max(1, len(labels)))
        )
        short = label if len(label) <= 14 else label[:13] + "..."
        parts.append(
            f'<text x="{x:.2f}" y="{top + plot_height + 28}" text-anchor="middle" class="xlabel">{html.escape(short)}</text>'
        )

    parts.append(
        f'<text x="{left + plot_width}" y="{height - 16}" text-anchor="end" class="metric">指标：{html.escape(metric_column)}</text>'
    )
    parts.append("</svg>")
    return "\n".join(parts)


def write_chart_html(
    path: str, question: str, plan: SemanticPlan, rows: Sequence[Dict[str, str]]
) -> None:
    labels, _, metric_column, dimension_columns = build_chart_points(rows)
    chart_type = infer_chart_type(rows, dimension_columns)
    chart_title = f"{question} - {metric_column}"
    svg = render_svg_chart(chart_title, rows, chart_type)
    payload = json.dumps(
        {
            "question": question,
            "sql": plan.sql,
            "chart_type": chart_type,
            "dimensions": dimension_columns,
            "metric": metric_column,
            "labels": labels,
            "rows": rows,
        },
        ensure_ascii=False,
        indent=2,
    )
    document = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(chart_title)}</title>
  <style>
    body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: #172033; background: #f7f8fb; }}
    main {{ max-width: 1080px; margin: 32px auto; padding: 0 24px; }}
    .panel {{ background: #fff; border: 1px solid #d9deea; border-radius: 8px; padding: 24px; box-shadow: 0 8px 28px rgba(25, 35, 65, 0.08); }}
    h1 {{ font-size: 22px; margin: 0 0 16px; }}
    pre {{ overflow: auto; background: #101827; color: #dbe7ff; padding: 16px; border-radius: 6px; font-size: 13px; }}
    svg {{ width: 100%; height: auto; display: block; }}
    .title {{ font-size: 20px; font-weight: 700; fill: #172033; }}
    .axis {{ stroke: #667085; stroke-width: 1.2; }}
    .grid {{ stroke: #e7eaf2; stroke-width: 1; }}
    .tick, .xlabel, .metric {{ fill: #667085; font-size: 12px; }}
    .bar {{ fill: #2f6fef; }}
    .line {{ fill: none; stroke: #2f6fef; stroke-width: 3; }}
    .point {{ fill: #ffffff; stroke: #2f6fef; stroke-width: 2.5; }}
    .value {{ fill: #172033; font-size: 12px; font-weight: 600; }}
    .empty {{ color: #667085; }}
  </style>
</head>
<body>
  <main>
    <section class="panel">
      {svg}
      <h1>SQL</h1>
      <pre>{html.escape(plan.sql)}</pre>
      <h1>Data</h1>
      <pre>{html.escape(payload)}</pre>
    </section>
  </main>
</body>
</html>
"""
    with open(path, "w", encoding="utf-8") as file:
        file.write(document)
