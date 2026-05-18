from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Optional, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _shared.runtime import load_local_module  # noqa: E402

_CORE = load_local_module(__file__, "core.py")
DashboardOrchestrationRequest = _CORE.DashboardOrchestrationRequest
run_dashboard_orchestration = _CORE.run_dashboard_orchestration


def parse_request_args(argv: Optional[Sequence[str]] = None) -> DashboardOrchestrationRequest:
    parser = argparse.ArgumentParser(
        description="Arrange dashboard layout for ChatBI overview data"
    )
    parser.add_argument("input_terms", nargs="*", help="Question or a JSON payload string")
    parser.add_argument("--input", help="Question or JSON payload; overrides positional args")
    parser.add_argument("--json", action="store_true", help="Print structured SkillResult JSON")
    args = parser.parse_args(argv)
    raw_input = args.input if args.input is not None else " ".join(args.input_terms)
    return DashboardOrchestrationRequest(raw_input=raw_input)


def run(argv: Optional[Sequence[str]] = None, context: Any = None) -> dict[str, Any]:
    return run_dashboard_orchestration(parse_request_args(argv), context)
