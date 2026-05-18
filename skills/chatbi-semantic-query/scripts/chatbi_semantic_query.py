#!/usr/bin/env python3
"""
Lightweight ChatBI semantic query script.

It maps a Chinese natural-language question to governed metric SQL using the
metadata tables in the demo MySQL database, then executes the generated query.
No Python MySQL package is required; the script uses the local `mysql` CLI.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Optional, Sequence

CURRENT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CURRENT_DIR))
sys.path.insert(0, str(CURRENT_DIR.parent))
sys.path.insert(0, str(CURRENT_DIR.parents[1]))

from _shared.runtime import load_local_module  # noqa: E402
from semantic_query import print_table  # noqa: E402

_API = load_local_module(__file__, "../api.py")


def main(argv: Optional[Sequence[str]] = None) -> int:
    tokens = list(sys.argv[1:] if argv is None else argv)
    try:
        request = _API.parse_request_args(tokens)
        payload = _API.run_query(request)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if "--show-sql" in tokens:
        print(payload["data"].get("sql", ""))
        print()
    if "--json" in tokens:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print_table(payload["data"].get("rows", []))
    if request.chart_html:
        print(f"\nchart: {request.chart_html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
