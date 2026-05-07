"""Vision table extraction helpers (no live LLM)."""

from __future__ import annotations

import unittest

from backend.vision.chart_table_extract import _coerce_payload


class VisionExtractTest(unittest.TestCase):
    def test_coerce_truncates_rows(self) -> None:
        rows = [{"a": str(i)} for i in range(100)]
        raw = {
            "columns": ["a"],
            "rows": rows,
            "confidence": 1.5,
            "notes": "ok",
        }
        out = _coerce_payload(raw, max_rows=5)
        self.assertEqual(len(out["rows"]), 5)
        self.assertEqual(out["confidence"], 1.0)

    def test_coerce_empty(self) -> None:
        out = _coerce_payload({}, max_rows=10)
        self.assertEqual(out["rows"], [])
        self.assertEqual(out["columns"], [])


if __name__ == "__main__":
    unittest.main()
