from __future__ import annotations

import sys
import types
import unittest

litellm_stub = types.ModuleType("litellm")
litellm_stub.acompletion = None
sys.modules.setdefault("litellm", litellm_stub)

from backend.agent.prompt_builder import AGENT_REACT_INSTRUCTION, AGENT_SYSTEM_INSTRUCTION
from backend.agent.runner import _build_steps, _is_query_plus_decision


class AgentWorkflowTest(unittest.TestCase):
    def test_runs_followup_decision_advice_for_query_plus_advice_request(self):
        plan = {"skill": "chatbi-semantic-query", "skill_args": ["1-4月销售额排行并给出决策建议"]}
        messages = [
            {
                "role": "user",
                "content": "1-4月销售额排行并给出决策建议",
            }
        ]

        self.assertTrue(_is_query_plus_decision(messages))

        steps = _build_steps(plan, messages)
        self.assertEqual(
            [step["skill"] for step in steps],
            [
                "chatbi-semantic-query",
                "chatbi-decision-advisor",
            ],
        )
        self.assertEqual(steps[1]["skill_args"], ["1-4月销售额排行并给出决策建议"])

    def test_overrides_decision_only_plan_for_compound_request(self):
        plan = {
            "skill": "chatbi-decision-advisor",
            "skill_args": ["1-4月销售额排行并给出经营决策建议"],
        }
        messages = [{"role": "user", "content": "1-4月销售额排行并给出经营决策建议"}]

        self.assertTrue(_is_query_plus_decision(messages))

        steps = _build_steps(plan, messages)
        self.assertEqual(
            [step["skill"] for step in steps],
            [
                "chatbi-semantic-query",
                "chatbi-decision-advisor",
            ],
        )
        self.assertEqual(steps[0]["skill_args"], ["1-4月销售额排行并给出经营决策建议"])

    def test_recognizes_decision_opinion_wording(self):
        plan = {"skill": "chatbi-semantic-query", "skill_args": ["1-4月销售额排行及决策意见"]}
        messages = [{"role": "user", "content": "1-4月销售额排行及决策意见"}]

        self.assertTrue(_is_query_plus_decision(messages))

        steps = _build_steps(plan, messages)
        self.assertEqual(
            [step["skill"] for step in steps],
            [
                "chatbi-semantic-query",
                "chatbi-decision-advisor",
            ],
        )

    def test_keeps_single_step_for_plain_query(self):
        plan = {"skill": "chatbi-semantic-query", "skill_args": ["1-4月销售额排行"]}
        messages = [{"role": "user", "content": "1-4月销售额排行"}]

        self.assertFalse(_is_query_plus_decision(messages))
        steps = _build_steps(plan, messages)
        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0]["skill"], "chatbi-semantic-query")

    def test_prompt_routes_database_overview_questions(self):
        for prompt in (AGENT_SYSTEM_INSTRUCTION, AGENT_REACT_INSTRUCTION):
            self.assertIn("chatbi-database-overview", prompt)
            self.assertIn("当前数据库有哪些表", prompt)

    def test_prompt_keeps_semantic_query_and_database_overview_rules(self):
        self.assertIn("chatbi-semantic-query", AGENT_SYSTEM_INSTRUCTION)
        self.assertIn("chatbi-database-overview", AGENT_SYSTEM_INSTRUCTION)


if __name__ == "__main__":
    unittest.main()
