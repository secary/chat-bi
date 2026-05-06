from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/chatbi-metric-explainer/scripts/explain_metric.py"
SPEC = importlib.util.spec_from_file_location("metric_explainer", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class FakeDb:
    def query(self, sql: str):
        if "FROM metric_definition" in sql:
            return [
                {
                    "metric_name": "销售额",
                    "metric_code": "sales_amount",
                    "source_table": "sales_order",
                    "formula": "SUM(sales_amount)",
                    "business_caliber": "统计周期内订单确认收入总额",
                    "default_dimensions": "时间、区域、部门、产品类别、渠道",
                },
                {
                    "metric_name": "毛利率",
                    "metric_code": "gross_profit_rate",
                    "source_table": "sales_order",
                    "formula": "SUM(gross_profit) / SUM(sales_amount)",
                    "business_caliber": "衡量业务盈利能力，销售额为 0 时不计算",
                    "default_dimensions": "时间、区域、产品类别、渠道",
                },
            ]
        if "FROM alias_mapping" in sql:
            return [
                {"alias_name": "收入", "standard_name": "销售额"},
                {"alias_name": "利润率", "standard_name": "毛利率"},
            ]
        if "FROM field_dictionary" in sql:
            return [
                {
                    "field_name": "gross_profit",
                    "business_name": "毛利",
                    "business_meaning": "销售额扣除直接成本后的利润",
                    "example_value": "63600.00",
                },
                {
                    "field_name": "sales_amount",
                    "business_name": "销售额",
                    "business_meaning": "订单确认收入金额",
                    "example_value": "172000.00",
                },
            ]
        return []


class MetricExplainerSkillTest(unittest.TestCase):
    def test_explains_metric_by_alias(self):
        result = MODULE.explain_metric("收入这个指标是什么意思", FakeDb())

        self.assertEqual(result["kind"], "metric_explanation")
        self.assertEqual(result["data"]["metric_name"], "销售额")
        self.assertIn("统计口径", result["text"])
        self.assertIn("常见别名", result["text"])

    def test_extracts_formula_fields_and_renders_details(self):
        result = MODULE.explain_metric("解释一下毛利率", FakeDb())

        self.assertEqual(result["data"]["metric_code"], "gross_profit_rate")
        self.assertEqual(
            [field["field_name"] for field in result["data"]["fields"]],
            ["gross_profit", "sales_amount"],
        )
        self.assertIn("gross_profit", result["text"])
        self.assertIn("sales_amount", result["text"])


if __name__ == "__main__":
    unittest.main()
