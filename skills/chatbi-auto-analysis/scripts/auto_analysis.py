#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional, Sequence

CURRENT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CURRENT_DIR.parent))
sys.path.insert(0, str(CURRENT_DIR.parents[1]))

from _shared.runtime import load_local_module  # noqa: E402

_API = load_local_module(__file__, "../api.py")


def main(argv: Optional[Sequence[str]] = None) -> int:
    try:
        request = _API.parse_request_args(argv)
        payload = _API.run_auto_analysis(request)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if "--json" in (argv or sys.argv[1:]):
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(payload.get("text", "自动分析完成。"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
