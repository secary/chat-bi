from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/chatbi-chart-recommendation/scripts/chart_recommendation_core.py"
SPEC = importlib.util.spec_from_file_location("chart_recommendation_core", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class ChartRecommendationSkillTest(unittest.TestCase):
    def test_returns_chart_option_for_ranking_rows(self):
        payload = MODULE.recommend_chart(
            "各区域销售额排名",
            [
                {"区域": "华东", "销售额": "613000"},
                {"区域": "华南", "销售额": "402000"},
            ],
        )

        self.assertEqual(payload["kind"], "chart_recommendation")
        self.assertEqual(payload["data"]["recommendation"]["status"], "ready")
        self.assertEqual(len(payload["charts"]), 1)
        self.assertEqual(payload["charts"][0]["series"][0]["type"], "bar")

    def test_returns_kpi_for_single_metric_row(self):
        payload = MODULE.recommend_chart(
            "4月销售额总览",
            [{"月份": "2026-04", "销售额": "172000"}],
        )

        self.assertEqual(payload["data"]["recommendation"]["recommended_chart"], "kpi_card")
        self.assertEqual(payload["kpis"][0]["label"], "销售额")

    def test_needs_rows_for_recommendation(self):
        payload = MODULE.recommend_chart("推荐一个图表", [])
        self.assertEqual(payload["data"]["recommendation"]["status"], "need_clarification")


if __name__ == "__main__":
    unittest.main()
