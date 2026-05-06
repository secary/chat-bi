from __future__ import annotations

import sys
import types
import unittest

litellm_stub = types.ModuleType("litellm")
litellm_stub.acompletion = None
sys.modules.setdefault("litellm", litellm_stub)

from backend.agent.runner import (
    build_execution_steps,
    deterministic_skill_override,
    infer_chart_plan,
    is_query_plus_decision_request,
    should_run_followup_decision_advice,
)


class AgentWorkflowTest(unittest.TestCase):
    def test_runs_followup_decision_advice_for_query_plus_advice_request(self):
        plan = {"skill": "chatbi-semantic-query", "skill_args": ["1-4月销售额排行并给出决策建议"]}
        messages = [
            {
                "role": "user",
                "content": "1-4月销售额排行并给出决策建议",
            }
        ]

        self.assertTrue(should_run_followup_decision_advice(plan, messages))

        steps = build_execution_steps(plan, messages)
        self.assertEqual([step["skill"] for step in steps], [
            "chatbi-semantic-query",
            "chatbi-decision-advisor",
        ])
        self.assertEqual(steps[1]["skill_args"], ["1-4月销售额排行并给出决策建议"])

    def test_overrides_decision_only_plan_for_compound_request(self):
        plan = {"skill": "chatbi-decision-advisor", "skill_args": ["1-4月销售额排行并给出经营决策建议"]}
        messages = [{"role": "user", "content": "1-4月销售额排行并给出经营决策建议"}]

        self.assertTrue(is_query_plus_decision_request(messages))
        self.assertTrue(should_run_followup_decision_advice(plan, messages))

        steps = build_execution_steps(plan, messages)
        self.assertEqual([step["skill"] for step in steps], [
            "chatbi-semantic-query",
            "chatbi-decision-advisor",
        ])
        self.assertEqual(steps[0]["skill_args"], ["1-4月销售额排行并给出经营决策建议"])

    def test_recognizes_decision_opinion_wording(self):
        plan = {"skill": "chatbi-semantic-query", "skill_args": ["1-4月销售额排行及决策意见"]}
        messages = [{"role": "user", "content": "1-4月销售额排行及决策意见"}]

        self.assertTrue(is_query_plus_decision_request(messages))
        self.assertTrue(should_run_followup_decision_advice(plan, messages))

        steps = build_execution_steps(plan, messages)
        self.assertEqual([step["skill"] for step in steps], [
            "chatbi-semantic-query",
            "chatbi-decision-advisor",
        ])

    def test_keeps_single_step_for_plain_query(self):
        plan = {"skill": "chatbi-semantic-query", "skill_args": ["1-4月销售额排行"]}
        messages = [{"role": "user", "content": "1-4月销售额排行"}]

        self.assertFalse(should_run_followup_decision_advice(plan, messages))
        self.assertFalse(is_query_plus_decision_request(messages))
        steps = build_execution_steps(plan, messages)
        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0]["skill"], "chatbi-semantic-query")

    def test_forces_semantic_query_for_grouped_metric_question(self):
        messages = [{"role": "user", "content": "按照产品划分销售额"}]

        self.assertEqual(deterministic_skill_override(messages), "chatbi-semantic-query")
        chart_plan = infer_chart_plan(messages[0]["content"])
        self.assertEqual(chart_plan["dimension"], "产品类别")
        self.assertEqual(chart_plan["metrics"], ["销售额"])

    def test_forces_metric_explainer_for_metric_definition_question(self):
        messages = [{"role": "user", "content": "销售额口径是什么"}]

        self.assertEqual(deterministic_skill_override(messages), "chatbi-metric-explainer")


if __name__ == "__main__":
    unittest.main()
