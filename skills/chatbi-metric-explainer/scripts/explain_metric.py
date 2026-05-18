#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from _shared.output import skill_response
from _shared.runtime import load_local_module


def main(argv: Optional[Sequence[str]] = None) -> int:
    tokens = list(sys.argv[1:] if argv is None else argv)
    api_module = load_local_module(__file__, "../api.py")
    try:
        request = api_module.parse_request_args(tokens)
        result = api_module.run_metric_explainer(request)
    except Exception as exc:
        if "--json" in tokens:
            print(json.dumps(skill_response("error", str(exc)), ensure_ascii=False))
            return 1
        print(f"错误：{exc}", file=sys.stderr)
        return 1

    if "--json" in tokens:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result["text"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
