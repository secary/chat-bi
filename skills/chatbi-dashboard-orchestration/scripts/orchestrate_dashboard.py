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

from _shared.trace import log_skill_event
from dashboard_orchestration_core import orchestrate_from_input


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Arrange dashboard layout for ChatBI overview data")
    parser.add_argument("input_terms", nargs="*", help="Question or a JSON payload string")
    parser.add_argument("--input", help="Question or JSON payload; overrides positional args")
    parser.add_argument("--json", action="store_true", help="Print structured SkillResult JSON")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    raw_input = args.input if args.input is not None else " ".join(args.input_terms)
    if not raw_input.strip():
        print("ERROR: input is required", file=sys.stderr)
        return 1

    log_skill_event(
        "skill.chatbi-dashboard-orchestration",
        "started",
        "dashboard orchestration started",
        {"input_preview": raw_input[:160]},
    )
    payload = orchestrate_from_input(raw_input)
    dashboard_spec = payload.get("data", {}).get("dashboard_spec", {})
    log_skill_event(
        "skill.chatbi-dashboard-orchestration",
        "completed",
        "dashboard orchestration completed",
        {
            "status": dashboard_spec.get("status"),
            "widget_count": len(dashboard_spec.get("widgets", []) or []),
            "chart_count": len(payload.get("charts", []) or []),
            "kpi_count": len(payload.get("kpis", []) or []),
        },
    )
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(payload.get("text", "看板编排完成。"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
