#!/usr/bin/env python3
"""
Generate rule-based ChatBI decision advice from demo MySQL metrics.
"""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Optional, Sequence

CURRENT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CURRENT_DIR.parent))
sys.path.insert(0, str(CURRENT_DIR.parents[1]))

import decision_advisor_core as advisor_core  # noqa: E402
from _shared.runtime import load_local_module  # noqa: E402

_API = load_local_module(__file__, "../api.py")


def main(argv: Optional[Sequence[str]] = None) -> int:
    tokens = list(sys.argv[1:] if argv is None else argv)
    try:
        request = _API.parse_request_args(tokens)
        payload = _API.run_decision_advisor(request)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if "--json" in tokens:
        print(advisor_core.dump_payload(payload))
    else:
        print(
            advisor_core.render_markdown(
                payload.get("data", {}).get("facts", {}),
                payload.get("data", {}).get("advices", []),
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
