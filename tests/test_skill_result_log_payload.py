from __future__ import annotations

import sys
import types
import unittest


litellm_stub = types.ModuleType("litellm")
litellm_stub.acompletion = None
sys.modules.setdefault("litellm", litellm_stub)

from backend.agent.executor import skill_result_log_payload


class SkillResultLogPayloadTest(unittest.TestCase):
    def test_extracts_query_intent_summary(self):
        result = {
            "kind": "semantic_intent",
            "text": "ok",
            "data": {
                "query_intent": {
                    "status": "ready",
                    "business_line": "corporate",
                    "intent_type": "ranking",
                    "metrics": [{"metric_id": "corporate_deposit_balance"}],
                    "dimensions": [{"dimension_id": "branch"}],
                    "missing_slots": [],
                }
            },
        }
        payload = skill_result_log_payload(result)
        self.assertEqual(payload["kind"], "semantic_intent")
        self.assertEqual(payload["query_intent"]["status"], "ready")
        self.assertEqual(
            payload["query_intent"]["metric_ids"], ["corporate_deposit_balance"]
        )


if __name__ == "__main__":
    unittest.main()
