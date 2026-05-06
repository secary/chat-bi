from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/chatbi-decision-advisor/scripts/generate_decision_advice.py"
SPEC = importlib.util.spec_from_file_location("decision_advisor_focus", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class DecisionAdvisorFocusTest(unittest.TestCase):
    def test_parses_focus_dimension_from_question(self):
        dimensions = MODULE.parse_focus_dimensions("1-4月销售额排行，重点分析维度：区域，并给出决策建议")
        self.assertIn("区域", dimensions)

    def test_region_focus_filters_out_channel_and_product_advice(self):
        facts = {
            "overview": {
                "target_achievement_rate": "1.06",
                "gross_margin_rate": "0.34",
                "sales": "1653000",
                "order_count": "442",
                "customer_count": "380",
            },
            "months": [
                {"month": "2026-01", "sales": "300000", "gross_margin_rate": "0.32", "target_achievement_rate": "0.98"},
                {"month": "2026-04", "sales": "500000", "gross_margin_rate": "0.35", "target_achievement_rate": "1.08"},
            ],
            "regions": [
                {"region": "华东", "sales": "610000", "target_achievement_rate": "1.12", "gross_margin_rate": "0.36"},
                {"region": "西南", "sales": "320000", "target_achievement_rate": "0.88", "gross_margin_rate": "0.31"},
            ],
            "channels": [
                {"channel": "线上", "sales": "700000", "gross_margin_rate": "0.29"},
                {"channel": "直销", "sales": "500000", "gross_margin_rate": "0.36"},
            ],
            "products": [
                {"product_category": "软件服务", "sales": "800000", "gross_margin_rate": "0.28"},
                {"product_category": "数据产品", "sales": "500000", "gross_margin_rate": "0.40"},
            ],
            "retention": [
                {"month": "2026-04", "retention_rate": "0.84", "churned_customers": "8"},
            ],
            "scope": {"focus_dimensions": ["区域"]},
        }

        advices = MODULE.build_advices(facts)
        themes = [item.theme for item in advices]
        self.assertIn("区域经营", themes)
        self.assertNotIn("渠道策略", themes)
        self.assertNotIn("产品组合", themes)


if __name__ == "__main__":
    unittest.main()
