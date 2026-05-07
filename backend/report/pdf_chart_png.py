"""Render ECharts-style option dict to PNG (matplotlib) for PDF embedding."""

from __future__ import annotations

import io
import sys
from typing import Any, Dict, List, Optional, Tuple

# Headless backend before pyplot import
import matplotlib
from matplotlib import font_manager

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

def _select_sans_fonts(installed: Optional[set[str]] = None) -> List[str]:
    names = installed
    if names is None:
        names = {f.name for f in font_manager.fontManager.ttflist}
    # Put CJK fonts before generic latin fonts to avoid tofu squares.
    candidates = [
        "Microsoft YaHei",
        "SimHei",
        "SimSun",
        "Noto Sans CJK SC",
        "Noto Sans CJK JP",
        "Noto Sans CJK TC",
        "Source Han Sans CN",
        "WenQuanYi Zen Hei",
        "Arial Unicode MS",
        "DejaVu Sans",
    ]
    picked = [name for name in candidates if name in names]
    if "DejaVu Sans" not in picked:
        picked.append("DejaVu Sans")
    return picked


if sys.platform == "win32":
    plt.rcParams["font.sans-serif"] = _select_sans_fonts()
else:
    plt.rcParams["font.sans-serif"] = _select_sans_fonts()
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["axes.unicode_minus"] = False


def _get_categories(option: Dict[str, Any]) -> List[str]:
    xa = option.get("xAxis")
    if isinstance(xa, list) and xa:
        xa = xa[0]
    if isinstance(xa, dict):
        data = xa.get("data")
        if isinstance(data, list):
            return [str(x) for x in data]
    return []


def _series_list(option: Dict[str, Any]) -> List[Dict[str, Any]]:
    s = option.get("series")
    if isinstance(s, list):
        return [x for x in s if isinstance(x, dict)]
    return []


def _parse_pie(
    option: Dict[str, Any],
) -> Optional[Tuple[List[str], List[float]]]:
    for ser in _series_list(option):
        if ser.get("type") == "pie":
            data = ser.get("data")
            if not isinstance(data, list):
                continue
            labels: List[str] = []
            values: List[float] = []
            for item in data:
                if isinstance(item, dict):
                    labels.append(str(item.get("name", "")))
                    try:
                        values.append(float(item.get("value", 0)))
                    except (TypeError, ValueError):
                        values.append(0.0)
            if labels and values:
                return labels, values
    return None


def _parse_bar_line(
    option: Dict[str, Any], want_type: str
) -> Optional[Tuple[List[str], List[Tuple[str, List[float]]]]]:
    cats = _get_categories(option)
    if not cats:
        return None
    series_data: List[Tuple[str, List[float]]] = []
    for ser in _series_list(option):
        if ser.get("type") != want_type:
            continue
        name = str(ser.get("name") or "series")
        raw = ser.get("data")
        if not isinstance(raw, list):
            continue
        vals: List[float] = []
        for v in raw:
            try:
                if isinstance(v, dict):
                    vals.append(float(v.get("value", 0)))
                else:
                    vals.append(float(v))
            except (TypeError, ValueError):
                vals.append(0.0)
        if len(vals) == len(cats):
            series_data.append((name, vals))
    if not series_data:
        return None
    return cats, series_data


def echarts_option_to_png_bytes(option: Any, dpi: int = 120) -> Optional[bytes]:
    """Return PNG bytes for supported chart types, or None."""
    if not isinstance(option, dict):
        return None

    fig, ax = plt.subplots(figsize=(6, 3.5), dpi=dpi)

    pie = _parse_pie(option)
    if pie:
        labels, values = pie
        ax.pie(values, labels=labels, autopct="%1.1f%%", textprops={"fontsize": 8})
        ax.axis("equal")
        title = option.get("title")
        if isinstance(title, dict) and title.get("text"):
            ax.set_title(str(title["text"]), fontsize=10)
        plt.tight_layout()
        return _fig_to_png(fig)

    for chart_type in ("bar", "line"):
        parsed = _parse_bar_line(option, chart_type)
        if not parsed:
            continue
        cats, series_data = parsed
        x = range(len(cats))
        if chart_type == "bar" and len(series_data) == 1:
            ax.bar(cats, series_data[0][1], color="#5470c6")
            for tick in ax.get_xticklabels():
                tick.set_rotation(25)
                tick.set_ha("right")
            ax.tick_params(axis="x", labelsize=8)
            ax.set_title(_chart_title(option) or "柱状图", fontsize=10)
            plt.tight_layout()
        elif chart_type == "bar":
            n = len(series_data)
            w = 0.8 / max(n, 1)
            for i, (name, vals) in enumerate(series_data):
                offset = -0.4 + w / 2 + i * w
                ax.bar(
                    [xi + offset for xi in x],
                    vals,
                    width=w * 0.95,
                    label=name,
                )
            ax.set_xticks(list(x))
            ax.set_xticklabels(cats, rotation=25, ha="right", fontsize=8)
            ax.legend(fontsize=7, loc="upper right")
            ax.set_title(_chart_title(option) or "分组柱状图", fontsize=10)
            plt.tight_layout()
        else:
            for name, vals in series_data:
                ax.plot(cats, vals, marker="o", label=name, linewidth=1.5)
            for tick in ax.get_xticklabels():
                tick.set_rotation(25)
                tick.set_ha("right")
            ax.legend(fontsize=7, loc="upper right")
            ax.grid(True, alpha=0.3)
            ax.set_title(_chart_title(option) or "折线图", fontsize=10)
            plt.tight_layout()
        return _fig_to_png(fig)

    plt.close(fig)
    return None


def _chart_title(option: Dict[str, Any]) -> str:
    t = option.get("title")
    if isinstance(t, dict) and t.get("text"):
        return str(t["text"])
    return ""


def _fig_to_png(fig: Any) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)
    return buf.getvalue()
