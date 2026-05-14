from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/chatbi-dashboard-orchestration/scripts/dashboard_orchestration_core.py"
SPEC = importlib.util.spec_from_file_location("dashboard_orchestration_core", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class DashboardOrchestrationSkillTest(unittest.TestCase):
    def test_builds_dashboard_spec_from_overview(self):
        payload = MODULE.build_dashboard_package(
            "经营概览",
            {
                "kpis": {
                    "total_sales": 1653000,
                    "row_count": 16,
                    "min_date": "2026-01-05",
                    "max_date": "2026-04-24",
                    "region_count": 4,
                },
                "sales_by_region": [{"region": "华东", "sales_amount": 613000}],
                "sales_by_month": [{"month": "2026-01", "sales_amount": 355000}],
                "customer_by_region": [{"region": "华东", "active_customers": 171}],
                "semantic_counts": {"alias_mapping": 20},
                "warnings": [],
            },
        )

        self.assertEqual(payload["kind"], "dashboard_orchestration")
        self.assertEqual(payload["data"]["dashboard_spec"]["status"], "ready")
        self.assertEqual(len(payload["charts"]), 3)
        self.assertEqual(payload["kpis"][0]["label"], "销售总额")

    def test_requires_source_data(self):
        payload = MODULE.build_dashboard_package("生成仪表盘", {})
        self.assertEqual(payload["data"]["dashboard_spec"]["status"], "need_clarification")

    def test_builds_dashboard_middleware_from_auto_analysis_payload(self):
        payload = MODULE.build_dashboard_package(
            "上传文件自动分析",
            {
                "auto_analysis": {
                    "profile": {"row_count": 3, "domain_guess": "generic_table"},
                    "metrics": [
                        {
                            "id": "llm_metric",
                            "name": "LLM 指标",
                            "rows": [{"月份": "2026-01", "LLM 指标": 10}],
                        }
                    ],
                    "charts": [{"xAxis": {"data": ["2026-01"]}, "series": []}],
                }
            },
        )

        self.assertEqual(payload["kind"], "dashboard_orchestration")
        self.assertEqual(payload["data"]["dashboard_spec"]["status"], "ready")
        self.assertEqual(payload["data"]["dashboard_middleware"]["widgets"][0]["id"], "llm_metric")

    def test_parse_input_supports_natural_language_plus_json(self):
        question, payload = MODULE.parse_input(
            "请帮我生成一个经营概览看板，并直接给出可视化结果："
            '{"question":"经营概览","kpis":{"total_sales":1653000,"row_count":16,'
            '"min_date":"2026-01-05","max_date":"2026-04-24","region_count":4},'
            '"sales_by_region":[{"region":"华东","sales_amount":613000}],'
            '"sales_by_month":[{"month":"2026-01","sales_amount":355000}],'
            '"customer_by_region":[{"region":"华东","active_customers":171}],'
            '"semantic_counts":{"alias_mapping":20},"warnings":[]}'
        )

        self.assertEqual(question, "经营概览")
        self.assertEqual(payload["kpis"]["region_count"], 4)


if __name__ == "__main__":
    unittest.main()
