from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/chatbi-file-ingestion/scripts/inspect_uploaded_table.py"


class FileIngestionSkillTest(unittest.TestCase):
    def test_reads_sales_order_csv_with_chinese_headers(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sales.csv"
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(
                    [
                        "订单日期",
                        "区域",
                        "部门",
                        "产品类别",
                        "产品名称",
                        "渠道",
                        "客户类型",
                        "销售额",
                        "订单数",
                        "客户数",
                        "毛利",
                        "目标销售额",
                    ]
                )
                writer.writerow(
                    [
                        "2026-04-03",
                        "华东",
                        "商业增长部",
                        "软件服务",
                        "智能分析平台",
                        "线上",
                        "企业客户",
                        "172000",
                        "48",
                        "41",
                        "63600",
                        "160000",
                    ]
                )

            proc = subprocess.run(
                [sys.executable, str(SCRIPT), str(path), "--json", "--include-rows"],
                cwd=ROOT,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                check=False,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )

        self.assertEqual(proc.returncode, 0, proc.stderr)
        result = json.loads(proc.stdout)
        self.assertEqual(result["kind"], "file_ingestion")
        self.assertTrue(result["data"]["valid"])
        self.assertEqual(result["data"]["table"], "sales_order")
        self.assertEqual(result["data"]["row_count"], 1)
        self.assertEqual(result["data"]["rows"][0]["region"], "华东")

    def test_reads_customer_profile_xlsx(self):
        try:
            from openpyxl import Workbook
        except ImportError:
            self.skipTest("openpyxl is not installed")

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "customer.xlsx"
            workbook = Workbook()
            sheet = workbook.active
            sheet.append(
                [
                    "月份",
                    "区域",
                    "客户类型",
                    "新增客户数",
                    "活跃客户数",
                    "留存客户数",
                    "流失客户数",
                ]
            )
            sheet.append(["2026-04-01", "华东", "企业客户", 21, 171, 149, 8])
            workbook.save(path)

            proc = subprocess.run(
                [sys.executable, str(SCRIPT), str(path), "--json"],
                cwd=ROOT,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                check=False,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )

        self.assertEqual(proc.returncode, 0, proc.stderr)
        result = json.loads(proc.stdout)
        self.assertEqual(result["data"]["table"], "customer_profile")
        self.assertTrue(result["data"]["valid"])
        self.assertEqual(result["data"]["preview_rows"][0]["region"], "华东")
        self.assertEqual(result["data"]["rows"], [])


if __name__ == "__main__":
    unittest.main()
