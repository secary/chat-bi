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


def main(argv: Optional[Sequence[str]] = None) -> None:
    tokens = list(sys.argv[1:] if argv is None else argv)
    api_module = load_local_module(__file__, "../api.py")
    try:
        request = api_module.parse_request_args(tokens)
        out = api_module.run_comparison(request)
    except RuntimeError as exc:
        out = skill_response("error", f"查询失败：{exc}")

    print(json.dumps(out, ensure_ascii=False, indent=2 if "--json" in tokens else None))


if __name__ == "__main__":
    main()
