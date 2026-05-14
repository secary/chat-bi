#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional, Sequence

CURRENT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CURRENT_DIR))
sys.path.insert(0, str(CURRENT_DIR.parents[1]))
sys.path.insert(0, str(CURRENT_DIR.parents[2]))

from _shared.trace import log_skill_event  # noqa: E402
from auto_analysis_core import analyze_from_input  # noqa: E402


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Auto-analyze uploaded table rows")
    parser.add_argument("input_terms", nargs="*", help="Question or JSON payload string")
    parser.add_argument("--input", help="Question or JSON payload; overrides positional args")
    parser.add_argument("--input-file", help="Read question/rows JSON payload from a file")
    parser.add_argument("--json", action="store_true", help="Print structured SkillResult JSON")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    if args.input_file:
        raw_input = Path(args.input_file).read_text(encoding="utf-8")
    else:
        raw_input = args.input if args.input is not None else " ".join(args.input_terms)
    if not raw_input.strip():
        print("ERROR: input is required", file=sys.stderr)
        return 1

    log_skill_event(
        "skill.chatbi-auto-analysis",
        "started",
        "auto analysis started",
        {"input_preview": raw_input[:160]},
    )
    payload = analyze_from_input(raw_input)
    log_skill_event(
        "skill.chatbi-auto-analysis",
        "completed",
        "auto analysis completed",
        {
            "status": payload.get("data", {}).get("status"),
            "chart_count": len(payload.get("charts", []) or []),
            "kpi_count": len(payload.get("kpis", []) or []),
        },
    )
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(payload.get("text", "自动分析完成。"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
