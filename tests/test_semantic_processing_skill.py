from __future__ import annotations

import importlib.util
import sys
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/chatbi-semantic-processing/scripts/semantic_processing_core.py"
SPEC = importlib.util.spec_from_file_location("semantic_processing_core", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class SemanticProcessingSkillTest(unittest.TestCase):
    def test_ready_ranking_query(self):
        result = MODULE.parse_question(
            "2026年4月对公存款余额按支行排名前10", today=date(2026, 5, 7)
        )

        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["business_line"], "corporate")
        self.assertEqual(result["intent_type"], "ranking")
        self.assertEqual(result["metrics"][0]["metric_id"], "corporate_deposit_balance")
        self.assertEqual(result["dimensions"][0]["dimension_id"], "branch")
        self.assertEqual(result["limit"], 10)
        self.assertEqual(result["time"]["time_range"]["start"], "2026-04-01")
        self.assertEqual(result["time"]["time_range"]["end"], "2026-04-30")

    def test_need_clarification_for_customer_ranking(self):
        result = MODULE.parse_question("客户排名", today=date(2026, 5, 7))

        self.assertEqual(result["status"], "need_clarification")
        self.assertIn("metric", result["missing_slots"])
        self.assertFalse(result["sql_readiness"]["ready_for_text_to_sql"])
        self.assertTrue(result["clarification_questions"])

    def test_trend_query_adds_time_dimension(self):
        result = MODULE.parse_question("2026年1-4月手机银行活跃用户数趋势", today=date(2026, 5, 7))

        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["intent_type"], "trend")
        self.assertEqual(result["metrics"][0]["metric_id"], "mobile_active_user_count")
        self.assertIn("time", [item["dimension_id"] for item in result["dimensions"]])
        self.assertEqual(result["time"]["time_range"]["start"], "2026-01-01")
        self.assertEqual(result["time"]["time_range"]["end"], "2026-04-30")


if __name__ == "__main__":
    unittest.main()
