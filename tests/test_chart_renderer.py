from __future__ import annotations

import unittest

from backend.renderers.chart import plan_to_option


class ChartRendererTest(unittest.TestCase):
    def test_infers_dimension_and_metrics_when_plan_missing_fields(self):
        rows = [
            {"区域": "华东", "销售额": "613000"},
            {"区域": "华南", "销售额": "402000"},
        ]
        plan = {"chart_type": "bar"}

        option = plan_to_option(plan, rows)

        self.assertEqual(option["xAxis"]["data"], ["华东", "华南"])
        self.assertEqual(option["series"][0]["name"], "销售额")
        self.assertEqual(option["series"][0]["data"], [613000.0, 402000.0])

    def test_keeps_empty_option_when_rows_missing(self):
        option = plan_to_option({"chart_type": "bar"}, [])
        self.assertEqual(option["title"]["text"], "暂无数据")

    def test_builds_heatmap_option(self):
        rows = [
            {"区域": "华东", "渠道": "直销", "成交率": "12.5"},
            {"区域": "华东", "渠道": "代理商", "成交率": "8.2"},
            {"区域": "华南", "渠道": "直销", "成交率": "9.3"},
        ]
        option = plan_to_option(
            {
                "chart_type": "heatmap",
                "dimension": "区域",
                "dimensions": ["区域", "渠道"],
                "secondary_dimension": "渠道",
                "metrics": ["成交率"],
            },
            rows,
        )

        self.assertEqual(option["series"][0]["type"], "heatmap")
        self.assertEqual(option["xAxis"]["data"], ["华东", "华南"])
        self.assertEqual(option["yAxis"]["data"], ["直销", "代理商"])

    def test_builds_funnel_option(self):
        rows = [
            {
                "统计期": "2026-04",
                "leads_count": "5405",
                "qualified_leads_count": "2009",
                "proposals_count": "1011",
                "closed_won_count": "385",
            }
        ]
        option = plan_to_option(
            {
                "chart_type": "funnel",
                "dimension": "统计期",
                "metrics": [
                    "leads_count",
                    "qualified_leads_count",
                    "proposals_count",
                    "closed_won_count",
                ],
            },
            rows,
        )

        self.assertEqual(option["series"][0]["type"], "funnel")
        self.assertEqual(option["series"][0]["data"][0]["name"], "leads_count")

    def test_builds_funnel_option_from_stage_rows(self):
        rows = [
            {"阶段": "线索", "转化漏斗": "5405"},
            {"阶段": "有效线索", "转化漏斗": "2009"},
            {"阶段": "方案/商机", "转化漏斗": "1011"},
            {"阶段": "成交", "转化漏斗": "385"},
        ]
        option = plan_to_option(
            {
                "chart_type": "funnel",
                "dimension": "阶段",
                "metrics": ["转化漏斗"],
            },
            rows,
        )

        self.assertEqual(option["series"][0]["type"], "funnel")
        self.assertEqual(option["series"][0]["data"][0]["name"], "线索")
        self.assertEqual(option["series"][0]["data"][0]["value"], 5405.0)


if __name__ == "__main__":
    unittest.main()
