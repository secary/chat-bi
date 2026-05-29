from __future__ import annotations

import unittest
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import patch

from backend.agent.execution_audit import audit_single_result_for_remediation
from backend.agent.execution_decider import decide_execution_mode
from backend.agent.runner import stream_chat
from backend.config import settings


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

    def test_post_audit_detects_missing_advice_after_fact_result(self) -> None:
        actions = audit_single_result_for_remediation(
            [{"role": "user", "content": "查华东销售额并给经营建议"}],
            {
                "kind": "table",
                "text": "查询完成",
                "data": {"rows": [{"区域": "华东", "销售额": "613000"}]},
            },
            "chatbi-semantic-query",
            ["text", "kpi_cards"],
        )

        self.assertEqual([action.skill for action in actions], ["chatbi-decision-advisor"])

    def test_stream_chat_single_post_audit_appends_decision_remediation(self) -> None:
        async def run() -> None:
            async def fake_legacy(*args, **kwargs):
                sink = kwargs["result_sink"]
                sink["last_result"] = {
                    "kind": "table",
                    "text": "查询完成",
                    "data": {"rows": [{"区域": "华东", "销售额": "613000"}]},
                }
                sink["last_skill_name"] = "chatbi-semantic-query"
                yield {"type": "text", "content": "查询完成"}
                yield {"type": "done", "content": None}

            def fake_followup(*args, **kwargs):
                return (
                    [{"type": "thinking", "content": "补充建议"}],
                    {"kind": "decision", "text": "建议聚焦华东", "data": {"advices": [{}]}},
                    [],
                )

            async def fake_stream_result_events(*args, **kwargs):
                yield {"type": "text", "content": "建议聚焦华东"}

            legacy = replace(settings, agent_react=False)
            skill_doc = SimpleNamespace(
                name="chatbi-decision-advisor",
                skill_dir=SimpleNamespace(name="chatbi-decision-advisor"),
            )
            with (
                patch("backend.agent.runner.settings", legacy),
                patch("backend.agent.runner._stream_chat_legacy", side_effect=fake_legacy),
                patch("backend.agent.runner.scan_skills_enabled", return_value=[skill_doc]),
                patch("backend.agent.runner.run_decision_followup", side_effect=fake_followup),
                patch(
                    "backend.agent.runner.stream_result_events",
                    side_effect=fake_stream_result_events,
                ),
            ):
                got = []
                async for event in stream_chat(
                    [{"role": "user", "content": "查华东销售额并给经营建议"}],
                    multi_agents="single",
                    trace_id="t-post-audit",
                ):
                    got.append(event)

            self.assertEqual(
                [event["type"] for event in got], ["text", "thinking", "thinking", "text", "done"]
            )
            self.assertEqual(got[-2]["content"], "建议聚焦华东")

        import asyncio

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
