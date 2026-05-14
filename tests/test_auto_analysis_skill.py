from __future__ import annotations

import importlib.util
import json
import tempfile
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "skills/chatbi-auto-analysis/scripts"
SCRIPT = SCRIPT_DIR / "auto_analysis_core.py"
sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location("auto_analysis_core", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)
import planner as PLANNER  # noqa: E402


class AutoAnalysisSkillTest(unittest.TestCase):
    def setUp(self):
        self._orig_planner = PLANNER.propose_metrics_with_llm
        PLANNER.propose_metrics_with_llm = lambda question, profile: [
            {
                "id": "llm_suggested_quality_ratio",
                "name": "质量指标趋势",
                "description": "LLM 根据字段画像建议的比例指标。",
                "formula_md": "`筛选金额 / 总金额 * 100%`",
                "group_by": [{"field": "start_date", "transform": "month", "alias": "月份"}],
                "formula": {
                    "op": "ratio_percent",
                    "numerator": {
                        "op": "sum",
                        "field": "principal",
                        "filter": {
                            "field": "loan_status",
                            "op": "contains",
                            "value": "逾期",
                        },
                    },
                    "denominator": {"op": "sum", "field": "principal"},
                },
                "chart_hint": "line",
                "confidence": 0.91,
                "selected": True,
            }
        ]

    def tearDown(self):
        PLANNER.propose_metrics_with_llm = self._orig_planner

    def test_proposes_frontend_renderable_metrics_for_uploaded_rows(self):
        payload = MODULE.execute_analysis(
            "帮我看看这张表适合分析什么",
            [
                {"start_date": "2026-01-03", "principal": "1000", "loan_status": "正常"},
                {"start_date": "2026-01-19", "principal": "3000", "loan_status": "逾期"},
            ],
            "propose",
            [],
        )

        proposal = payload["data"]["analysis_proposal"]
        self.assertEqual(payload["data"]["status"], "need_confirmation")
        self.assertIn("采纳全部指标", proposal["markdown"])
        self.assertEqual(proposal["dataset"]["domain_guess"], "loan_risk")
        self.assertEqual(proposal["proposed_metrics"][0]["id"], "llm_suggested_quality_ratio")

    def test_executes_selected_metric_and_returns_dashboard_middleware(self):
        raw = json.dumps(
            {
                "question": "采纳全部指标",
                "mode": "execute",
                "metric_plans": PLANNER.propose_metrics_with_llm("", {}),
                "rows": [
                    {
                        "start_date": "2026-01-03",
                        "principal": "1000",
                        "loan_status": "正常",
                    },
                    {
                        "start_date": "2026-01-19",
                        "principal": "3000",
                        "loan_status": "逾期",
                    },
                    {
                        "start_date": "2026-02-01",
                        "principal": "2000",
                        "loan_status": "正常",
                    },
                ],
            },
            ensure_ascii=False,
        )

        payload = MODULE.analyze_from_input(raw)

        self.assertEqual(payload["data"]["status"], "ready")
        self.assertEqual(payload["data"]["metrics"][0]["rows"][0]["质量指标趋势"], 75.0)
        self.assertEqual(payload["charts"][0]["xAxis"]["data"], ["2026-01", "2026-02"])
        self.assertIn("dashboard_middleware", payload["data"])

    def test_cli_reads_payload_from_input_file(self):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json") as handle:
            json.dump(
                {
                    "question": "先推荐指标",
                    "rows": [{"month": "2026-01", "amount": "100"}],
                },
                handle,
                ensure_ascii=False,
            )
            handle.flush()

            from auto_analysis import main

            self.assertEqual(main(["--input-file", handle.name, "--json"]), 0)

    def test_executes_formula_tree_without_metric_specific_branches(self):
        roi_like_plan = {
            "id": "llm_defined_ratio",
            "name": "投产效率",
            "description": "由 LLM 计划给出的通用公式。",
            "formula_md": "`(revenue - cost) / cost * 100%`",
            "group_by": [{"field": "month", "transform": "month", "alias": "月份"}],
            "formula": {
                "op": "ratio_percent",
                "numerator": {
                    "op": "subtract",
                    "left": {"op": "sum", "field": "revenue"},
                    "right": {"op": "sum", "field": "cost"},
                },
                "denominator": {"op": "sum", "field": "cost"},
            },
            "chart_hint": "line",
            "confidence": 0.9,
            "selected": True,
        }
        payload = MODULE.execute_analysis(
            "确认生成投产效率趋势",
            [
                {"month": "2026-01", "revenue": "150", "cost": "100"},
                {"month": "2026-02", "revenue": "240", "cost": "200"},
            ],
            "execute",
            ["llm_defined_ratio"],
            metric_plans=[roi_like_plan],
        )

        metric = next(
            item for item in payload["data"]["metrics"] if item["id"] == "llm_defined_ratio"
        )
        self.assertEqual(
            metric["rows"],
            [{"月份": "2026-01", "投产效率": 50.0}, {"月份": "2026-02", "投产效率": 20.0}],
        )

    def test_executes_uploaded_file_distribution_count_plan(self):
        status_count_plan = {
            "id": "account_status_count",
            "name": "账户状态统计",
            "description": "按账户状态统计记录数。",
            "formula_md": "`count()`",
            "group_by": [{"field": "账户状态", "alias": "账户状态"}],
            "formula": {"op": "count"},
            "chart_hint": "bar",
            "confidence": 0.9,
            "selected": True,
        }
        payload = MODULE.execute_analysis(
            "确认按账户状态做统计",
            [
                {"账户状态": "正常", "账户类型": "活期", "余额": "1000"},
                {"账户状态": "正常", "账户类型": "定期", "余额": "2000"},
                {"账户状态": "冻结", "账户类型": "活期", "余额": "300"},
            ],
            "execute",
            ["account_status_count"],
            metric_plans=[status_count_plan],
        )

        metric = payload["data"]["metrics"][0]
        self.assertEqual(payload["data"]["status"], "ready")
        self.assertEqual(
            metric["rows"],
            [{"账户状态": "冻结", "账户状态统计": 1.0}, {"账户状态": "正常", "账户状态统计": 2.0}],
        )

    def test_executes_uploaded_file_overdue_rate_plan_with_generic_fields(self):
        overdue_rate_plan = {
            "id": "overdue_rate_by_product",
            "name": "逾期率",
            "description": "按业务品种计算逾期记录占比。",
            "formula_md": "`逾期记录数 / 记录数 * 100%`",
            "group_by": [{"field": "业务品种", "alias": "业务品种"}],
            "formula": {
                "op": "ratio_percent",
                "numerator": {
                    "op": "count",
                    "filter": {"field": "账户状态", "op": "contains", "value": "逾期"},
                },
                "denominator": {"op": "count"},
            },
            "chart_hint": "bar",
            "confidence": 0.9,
            "selected": True,
        }
        payload = MODULE.execute_analysis(
            "确认分析逾期情况统计",
            [
                {"业务品种": "房贷", "未还本金": "800000", "账户状态": "正常"},
                {"业务品种": "经营贷", "未还本金": "300000", "账户状态": "逾期"},
                {"业务品种": "经营贷", "未还本金": "120000", "账户状态": "逾期"},
            ],
            "execute",
            ["overdue_rate_by_product"],
            metric_plans=[overdue_rate_plan],
        )

        metric = payload["data"]["metrics"][0]
        self.assertEqual(payload["data"]["status"], "ready")
        self.assertEqual(
            metric["rows"],
            [{"业务品种": "房贷", "逾期率": 0.0}, {"业务品种": "经营贷", "逾期率": 100.0}],
        )


if __name__ == "__main__":
    unittest.main()
