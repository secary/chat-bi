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


if __name__ == "__main__":
    unittest.main()
