from __future__ import annotations

import unittest

from backend.agent.harness_policy import authorize_action
from backend.agent.harness_schema import validate_harness_action
from backend.agent.harness_state import HarnessState


class HarnessSchemaTest(unittest.TestCase):
    def test_validate_call_skill_requires_list_args(self):
        result = validate_harness_action(
            {"action": "call_skill", "skill": "chatbi-semantic-query", "skill_args": "oops"}
        )
        self.assertFalse(result.ok)
        self.assertIn("skill_args", result.reason)

    def test_validate_aliases_ask_and_done(self):
        ask = validate_harness_action({"action": "ask", "text": "请补充时间范围"})
        done = validate_harness_action({"action": "done", "text": "结束"})
        self.assertTrue(ask.ok)
        self.assertEqual(ask.action.action, "ask_clarification")
        self.assertTrue(done.ok)
        self.assertEqual(done.action.action, "finish")


class HarnessPolicyTest(unittest.TestCase):
    def test_decision_advisor_requires_query_result(self):
        state = HarnessState(trace_id="t", user_text="给建议", max_steps=4)
        action = validate_harness_action(
            {"action": "call_skill", "skill": "chatbi-decision-advisor", "skill_args": []}
        ).action
        decision = authorize_action(action, state, ["chatbi-decision-advisor"], messages=[])
        self.assertFalse(decision.ok)
        self.assertIn("查询结果之后", decision.reason)

    def test_chart_recommendation_accepts_rows_context(self):
        state = HarnessState(trace_id="t", user_text="画图", max_steps=4)
        state.record_skill(
            "chatbi-semantic-query",
            {"kind": "table", "data": {"rows": [{"月份": "2026-01", "销售额": "100"}]}},
        )
        action = validate_harness_action(
            {"action": "call_skill", "skill": "chatbi-chart-recommendation", "skill_args": []}
        ).action
        decision = authorize_action(action, state, ["chatbi-chart-recommendation"], messages=[])
        self.assertTrue(decision.ok)


if __name__ == "__main__":
    unittest.main()
