from __future__ import annotations

import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_DIR))

from chart_recommendation_core import *  # noqa: E402,F401,F403
