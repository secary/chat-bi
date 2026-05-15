from __future__ import annotations

import json
import unittest

from backend.agent.observation import summarize_observation


class ObservationTest(unittest.TestCase):
    def test_summarize_table_includes_row_count_and_samples(self):
        result = {
            "kind": "table",
            "text": "查询完成",
            "data": {
                "rows": [
                    {"a": "1"},
                    {"a": "2"},
                    {"a": "3"},
                    {"a": "4"},
                    {"a": "5"},
                    {"a": "6"},
                ]
            },
        }
        raw = summarize_observation("chatbi-semantic-query", result)
        payload = json.loads(raw)
        self.assertEqual(payload["row_count"], 6)
        self.assertEqual(len(payload["sample_rows"]), 5)

    def test_summarize_semantic_empty_rows_includes_sql_and_contradiction_hint(self):
        sql = (
            "SELECT 1 FROM `sales_order` WHERE `region` = '华东' AND `region` = '华北' "
            "AND `order_date` >= '2026-01-01'"
        )
        result = {
            "kind": "table",
            "text": "查询完成，未返回数据。",
            "data": {"rows": [], "sql": sql},
        }
        raw = summarize_observation("chatbi-semantic-query", result)
        payload = json.loads(raw)
        self.assertEqual(payload["row_count"], 0)
        self.assertIn("sql_excerpt", payload)
        self.assertIn("empty_result_hint", payload)

    def test_summarize_comparison_includes_comparison_period(self):
        result = {
            "kind": "table",
            "text": "2026年2月 vs 1月",
            "data": {
                "rows": [{"dimension": "华东", "2月销售额": 100, "1月销售额": 90}],
                "comparison_meta": {"year": 2026, "cur_month": 2, "prev_month": 1},
            },
        }
        raw = summarize_observation("chatbi-comparison", result)
        payload = json.loads(raw)
        self.assertEqual(
            payload["comparison_period"],
            {"year": 2026, "cur_month": 2, "prev_month": 1},
        )


if __name__ == "__main__":
    unittest.main()
