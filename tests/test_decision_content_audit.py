from __future__ import annotations

import unittest

from backend.agent.decision_content_audit import audit_decision_result


class DecisionContentAuditTest(unittest.TestCase):
    def test_flags_missing_core_facts(self):
        result = {
            "kind": "decision",
            "data": {
                "facts": {"overview": {"sales": "1000"}},
                "advices": [
                    {
                        "theme": "增长目标",
                        "decision": "上调目标",
                        "reason": "销量较高",
                        "actions": ["复盘打法"],
                    }
                ],
            },
        }
        audit = audit_decision_result(result)
        codes = {item["code"] for item in audit["issues"]}
        self.assertIn("FACTS_MISSING_FOR_DECISION", codes)

    def test_flags_generic_and_ungrounded_advice(self):
        result = {
            "kind": "decision",
            "data": {
                "facts": {
                    "overview": {
                        "sales": "1000",
                        "target_achievement_rate": "1.02",
                        "gross_margin_rate": "0.33",
                    },
                    "scope": {},
                },
                "advices": [
                    {
                        "theme": "增长目标",
                        "decision": "继续推进并优化策略。",
                        "reason": "建议保持关注。",
                        "actions": ["加强管理", "持续跟进"],
                    }
                ],
            },
        }
        audit = audit_decision_result(result)
        codes = {item["code"] for item in audit["issues"]}
        self.assertIn("DECISION_ADVICE_TOO_GENERIC", codes)
        self.assertIn("DECISION_ADVICE_NOT_GROUNDED", codes)

    def test_flags_scope_mismatch(self):
        result = {
            "kind": "decision",
            "data": {
                "facts": {
                    "overview": {
                        "sales": "1000",
                        "target_achievement_rate": "1.02",
                        "gross_margin_rate": "0.33",
                    },
                    "scope": {"focus_dimensions": ["区域"]},
                },
                "advices": [
                    {
                        "theme": "渠道策略",
                        "decision": "优化线上渠道投放。",
                        "reason": "线上渠道销售额为2000元，毛利率为20%。",
                        "actions": ["复核投放结构"],
                    }
                ],
            },
        }
        audit = audit_decision_result(result)
        codes = {item["code"] for item in audit["issues"]}
        self.assertIn("DECISION_SCOPE_MISMATCH", codes)


if __name__ == "__main__":
    unittest.main()
