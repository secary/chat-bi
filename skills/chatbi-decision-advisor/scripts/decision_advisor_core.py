from __future__ import annotations

import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_DIR))

from _shared.runtime import load_local_module  # noqa: E402

_ENGINE = load_local_module(__file__, "../engine.py")
globals().update(
    {name: getattr(_ENGINE, name) for name in dir(_ENGINE) if not name.startswith("_")}
)
