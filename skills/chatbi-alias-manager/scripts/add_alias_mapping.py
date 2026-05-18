#!/usr/bin/env python3
"""
Add ChatBI semantic aliases to alias_mapping.

This script is intentionally small and deterministic: it validates that the
target standard metric/dimension exists, then inserts a missing alias into the
demo MySQL metadata table. It uses the local `mysql` CLI, so no Python MySQL
package is required.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from _shared.runtime import load_local_module


def main(argv: Optional[Sequence[str]] = None) -> int:
    tokens = list(sys.argv[1:] if argv is None else argv)
    api_module = load_local_module(__file__, "../api.py")
    try:
        request = api_module.parse_request_args(tokens)
        payload = api_module.run_alias_manager(request)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if "--json" in tokens:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    print(payload["text"])
    if "--print-init-sql" in tokens:
        print(payload["data"]["init_sql"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
