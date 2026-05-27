from __future__ import annotations

import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.agent.multi_agent_summarize import call_summarize_llm


class MultiAgentSummarizeTest(unittest.TestCase):
    def test_summarizer_hides_internal_route_metadata(self) -> None:
        async def run() -> None:
            mock_resp = MagicMock()
            mock_resp.choices = [MagicMock(message=MagicMock(content=json.dumps({"text": "ok"})))]
            captured = {}

            async def fake_completion(*args, **kwargs):
                captured["messages"] = kwargs["messages"]
                return mock_resp

            with patch(
                "backend.agent.multi_agent_summarize.chatbi_acompletion",
                new_callable=AsyncMock,
                side_effect=fake_completion,
            ):
                got = await call_summarize_llm(
                    "查华东销售额",
                    [
                        {
                            "agent": "demo_query",
                            "label": "B线",
                            "handoff_instruction": "查询华东销售额",
                            "observation": "查询结果：华东销售额 613000.00 元",
                        }
                    ],
                    trace_id="t-summary-public",
                )

            self.assertEqual(got, {"text": "ok"})
            user_body = captured["messages"][1]["content"]
            self.assertIn("results", user_body)
            self.assertIn("613000.00", user_body)
            self.assertNotIn("demo_query", user_body)
            self.assertNotIn("B线", user_body)
            self.assertNotIn("handoff_instruction", user_body)
            self.assertNotIn("specialists", user_body)

        import asyncio

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
