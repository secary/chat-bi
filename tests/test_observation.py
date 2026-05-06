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


if __name__ == "__main__":
    unittest.main()
