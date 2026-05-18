from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Optional, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _shared.runtime import load_local_module  # noqa: E402

_CORE = load_local_module(__file__, "core.py")
MetricExplainerRequest = _CORE.MetricExplainerRequest
run_metric_explainer = _CORE.run_metric_explainer


def parse_request_args(argv: Optional[Sequence[str]] = None) -> MetricExplainerRequest:
    parser = argparse.ArgumentParser(description="Explain a governed ChatBI metric.")
    parser.add_argument("question", nargs="+", help="Chinese metric explanation question")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--host")
    parser.add_argument("--port")
    parser.add_argument("--user")
    parser.add_argument("--password")
    parser.add_argument("--database")
    args = parser.parse_args(argv)
    return MetricExplainerRequest(question=" ".join(args.question))


def run(argv: Optional[Sequence[str]] = None, context: Any = None) -> dict[str, Any]:
    return run_metric_explainer(parse_request_args(argv), context)
