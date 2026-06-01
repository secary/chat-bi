from __future__ import annotations

import unittest

from backend.agent.multi_agent_intent import (
    build_initial_plan_from_intent,
    build_next_plan_from_intent,
    classify_multi_agent_intent,
    route_sequence_from_intent,
)


class MultiAgentIntentTest(unittest.TestCase):
    def test_classifies_query_then_decide(self) -> None:
        intent = classify_multi_agent_intent(
            [{"role": "user", "content": "基于华东近3个月销售和毛利给我3条经营建议"}]
        )
        assert intent is not None
        self.assertEqual(intent["intent_type"], "query_then_decide")
        self.assertEqual(intent["current_route"], "demo_query")
        self.assertEqual(route_sequence_from_intent(intent), ["demo_query", "business_advisor"])
        self.assertIn("advice", intent["final_outputs"])

    def test_classifies_query_then_decide_then_viz(self) -> None:
        intent = classify_multi_agent_intent(
            [{"role": "user", "content": "查华东销售和毛利，给建议，并画趋势图"}]
        )
        assert intent is not None
        self.assertEqual(intent["intent_type"], "query_then_decide_then_viz")
        self.assertEqual(intent["current_route"], "demo_query")
        self.assertEqual(
            route_sequence_from_intent(intent),
            ["demo_query", "business_advisor", "viz_board"],
        )

    def test_pure_decision_stays_single_route(self) -> None:
        intent = classify_multi_agent_intent([{"role": "user", "content": "给我经营建议"}])
        assert intent is not None
        self.assertEqual(intent["current_route"], "business_advisor")
        self.assertEqual(route_sequence_from_intent(intent), ["business_advisor"])

    def test_single_query_still_gets_controlled_route(self) -> None:
        intent = classify_multi_agent_intent([{"role": "user", "content": "查华东销售额"}])
        assert intent is not None
        self.assertEqual(intent["intent_type"], "query_only")
        self.assertEqual(intent["current_route"], "demo_query")
        self.assertEqual(route_sequence_from_intent(intent), ["demo_query"])

    def test_chart_advice_without_data_need_does_not_force_query_route(self) -> None:
        intent = classify_multi_agent_intent(
            [{"role": "user", "content": "建议用柱状图还是折线图"}]
        )

        self.assertIsNone(intent)

    def test_query_with_chart_still_routes_query_then_viz(self) -> None:
        intent = classify_multi_agent_intent(
            [{"role": "user", "content": "查华东销售额并画柱状图"}]
        )
        assert intent is not None
        self.assertEqual(intent["intent_type"], "query_then_viz")
        self.assertEqual(route_sequence_from_intent(intent), ["demo_query", "viz_board"])

    def test_builds_initial_and_next_route_plans(self) -> None:
        intent = classify_multi_agent_intent(
            [{"role": "user", "content": "先查询华东销售额，再给经营建议"}]
        )
        assert intent is not None
        first = build_initial_plan_from_intent(intent)
        assert first is not None
        self.assertEqual(first["tasks"][0]["agent_id"], "demo_query")
        self.assertFalse(first["finalize_after_this_batch"])

        second = build_next_plan_from_intent(intent, completed_agents=["demo_query"])
        assert second is not None
        self.assertEqual(second["tasks"][0]["agent_id"], "business_advisor")
        self.assertTrue(second["finalize_after_this_batch"])


if __name__ == "__main__":
    unittest.main()
