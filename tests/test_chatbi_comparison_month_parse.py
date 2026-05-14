"""Month parsing for chatbi-comparison (e.g. 1月份 vs 1月)."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/chatbi-comparison/scripts/chatbi_comparison.py"
SPEC = importlib.util.spec_from_file_location("chatbi_comparison_core", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class FakeDb:
    def query(self, _sql: str):
        return [{"m": 4}]


class ChatbiComparisonMonthParseTest(unittest.TestCase):
    def test_pair_month_fen_matches(self) -> None:
        year, cur, prev = MODULE.detect_months("1月份和2月份的环比怎么样？", FakeDb())
        self.assertEqual(year, 2026)
        self.assertEqual(cur, 2)
        self.assertEqual(prev, 1)

    def test_pair_mixed_fen(self) -> None:
        year, cur, prev = MODULE.detect_months("1月份和2月销售额环比", FakeDb())
        self.assertEqual((year, cur, prev), (2026, 2, 1))

    def test_pair_classic(self) -> None:
        year, cur, prev = MODULE.detect_months("1月和2月销售额环比", FakeDb())
        self.assertEqual((year, cur, prev), (2026, 2, 1))

    def test_single_month_fen(self) -> None:
        year, cur, prev = MODULE.detect_months("3月份销售额环比", FakeDb())
        self.assertEqual(year, 2026)
        self.assertEqual(cur, 3)
        self.assertEqual(prev, 2)


if __name__ == "__main__":
    unittest.main()
