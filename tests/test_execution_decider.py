from __future__ import annotations

import unittest
from unittest.mock import patch

from backend.agent.execution_decider import decide_execution_mode
from backend.agent.runner import stream_chat


class ExecutionDeciderTest(unittest.TestCase):
    def test_query_only_uses_single_agent(self) -> None:
        decision = decide_execution_mode([{"role": "user", "content": "查华东销售额"}])

        self.assertEqual(decision.mode, "single")
        self.assertEqual(decision.route_sequence, ["demo_query"])
        self.assertGreaterEqual(decision.confidence, 0.8)

    def test_query_then_decision_uses_multi_agent(self) -> None:
        decision = decide_execution_mode(
            [{"role": "user", "content": "基于华东近3个月销售和毛利给我经营建议"}]
        )

        self.assertEqual(decision.mode, "multi")
        self.assertEqual(decision.route_sequence, ["demo_query", "business_advisor"])
        self.assertIn("composite_goal", decision.risk_flags)

    def test_pure_decision_asks_for_facts(self) -> None:
        decision = decide_execution_mode([{"role": "user", "content": "给我经营建议"}])

        self.assertEqual(decision.mode, "ask")
        self.assertEqual(decision.route_sequence, ["business_advisor"])
        self.assertIn("decision_without_facts", decision.risk_flags)

    def test_stream_chat_auto_dispatches_composite_input_to_multi_agent(self) -> None:
        async def run() -> None:
            captured = {}

            async def fake_multi(*args, **kwargs):
                captured["controlled_intent"] = kwargs.get("controlled_intent")
                yield {"type": "text", "content": "multi ok"}
                yield {"type": "done", "content": None}

            with patch(
                "backend.agent.multi_agent_runner.stream_chat_multi_agent",
                side_effect=fake_multi,
            ):
                got = []
                async for event in stream_chat(
                    [{"role": "user", "content": "基于华东近3个月销售和毛利给经营建议"}],
                    trace_id="t-auto-decision",
                ):
                    got.append(event)

            self.assertEqual(got[-2]["content"], "multi ok")
            self.assertEqual(captured["controlled_intent"]["intent_type"], "query_then_decide")

        import asyncio

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
