from __future__ import annotations

import asyncio
import unittest

from backend.agent.formatter import stream_result_events
from backend.agent.protocol import normalize_skill_result


class SkillProtocolTest(unittest.TestCase):
    def test_normalizes_legacy_table_rows(self):
        result = normalize_skill_result([{"区域": "华东", "销售额": "100"}], "demo")

        self.assertEqual(result["kind"], "table")
        self.assertEqual(result["data"]["rows"][0]["区域"], "华东")
        self.assertIn("查询完成", result["text"])

    def test_streams_structured_decision_result(self):
        result = {
            "kind": "decision",
            "text": "## 决策建议",
            "data": {},
            "kpis": [{"label": "销售额", "value": "100", "unit": "元", "status": "neutral"}],
        }

        async def collect():
            return [
                event
                async for event in stream_result_events(
                    "chatbi-decision-advisor", {}, result
                )
            ]

        events = asyncio.run(collect())
        self.assertEqual(events[0], {"type": "text", "content": "## 决策建议"})
        self.assertEqual(events[1]["type"], "kpi_cards")


if __name__ == "__main__":
    unittest.main()
