from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/chatbi-database-overview/scripts/database_overview.py"
SPEC = importlib.util.spec_from_file_location("database_overview", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class FakeDb:
    def query(self, sql: str):
        if "information_schema.TABLES" in sql:
            return [
                {"table_name": "sales_order", "table_type": "VIEW"},
                {"table_name": "customer_profile", "table_type": "VIEW"},
                {"table_name": "field_dictionary", "table_type": "BASE TABLE"},
                {"table_name": "metric_definition", "table_type": "BASE TABLE"},
                {"table_name": "alias_mapping", "table_type": "BASE TABLE"},
            ]
        if "information_schema.COLUMNS" in sql:
            return [
                {"table_name": "sales_order", "column_name": "region", "column_type": "varchar(50)", "ordinal_position": "1"},
                {"table_name": "sales_order", "column_name": "sales_amount", "column_type": "decimal(14,2)", "ordinal_position": "2"},
                {"table_name": "customer_profile", "column_name": "active_customers", "column_type": "int", "ordinal_position": "1"},
                {"table_name": "metric_definition", "column_name": "metric_name", "column_type": "varchar(80)", "ordinal_position": "1"},
            ]
        if "FROM field_dictionary" in sql:
            return [
                {"table_name": "sales_order", "field_name": "region", "business_name": "区域", "business_meaning": "经营区域"},
                {"table_name": "sales_order", "field_name": "sales_amount", "business_name": "业务规模", "business_meaning": "银行业务余额"},
            ]
        if "FROM metric_definition" in sql and "information_schema" not in sql:
            return [
                {
                    "metric_name": "销售额",
                    "metric_code": "sales_amount",
                    "source_table": "sales_order",
                    "formula": "SUM(sales_amount)",
                    "default_dimensions": "时间、区域",
                }
            ]
        if "FROM dimension_definition" in sql:
            return [
                {"dimension_name": "区域", "field_name": "region", "source_table": "sales_order"}
            ]
        if "COUNT(*)" in sql:
            return [{"row_count": "16"}]
        return []


class DatabaseOverviewSkillTest(unittest.TestCase):
    def test_separates_business_and_semantic_assets(self):
        result = MODULE.database_overview(FakeDb(), "chatbi_bank_external")

        self.assertEqual(result["kind"], "database_overview")
        self.assertEqual(len(result["data"]["business_assets"]), 2)
        self.assertEqual(len(result["data"]["semantic_assets"]), 3)
        self.assertIn("可直接查询的业务表/视图：2 张", result["text"])

    def test_enriches_columns_and_metrics(self):
        result = MODULE.database_overview(FakeDb(), "chatbi_bank_external")
        sales = next(
            asset
            for asset in result["data"]["business_assets"]
            if asset["name"] == "sales_order"
        )

        self.assertEqual(sales["columns"][0]["business_name"], "区域")
        self.assertEqual(result["data"]["metrics"][0]["metric_name"], "销售额")
        self.assertIn("销售额", result["text"])


if __name__ == "__main__":
    unittest.main()
