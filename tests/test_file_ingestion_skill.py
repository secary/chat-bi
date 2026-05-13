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
        self.assertEqual(result["data"]["analysis_mode"], "schema_direct")
        self.assertEqual(result["data"]["row_count"], 1)
        self.assertEqual(result["data"]["rows"][0]["region"], "华东")
        self.assertEqual(result["data"]["analysis"]["key_metrics"][0]["label"], "总销售额")

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
        self.assertEqual(result["data"]["analysis_mode"], "schema_direct")
        self.assertEqual(result["data"]["preview_rows"][0]["region"], "华东")
        self.assertEqual(result["data"]["rows"], [])

    def test_falls_back_to_pandas_analysis_for_non_governed_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "generic.csv"
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["门店", "城市", "评分", "客流"])
                writer.writerow(["南京东路店", "上海", "4.7", "321"])
                writer.writerow(["万象城店", "深圳", "4.5", "280"])

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
        self.assertFalse(result["data"]["valid"])
        self.assertEqual(result["data"]["analysis_mode"], "pandas_fallback")
        self.assertEqual(result["data"]["analysis"]["summary_title"], "Pandas 通用表格分析")
        self.assertEqual(result["data"]["analysis"]["shape"]["rows"], 2)
        self.assertIn("评分", result["data"]["analysis"]["columns"])

    def test_pandas_fallback_answers_question_with_distribution_stats(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "deposit.csv"
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["账户状态", "账户类型", "余额"])
                writer.writerow(["正常", "活期", "1000"])
                writer.writerow(["正常", "定期", "2000"])
                writer.writerow(["冻结", "活期", "300"])

            proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    str(path),
                    "--json",
                    "--question",
                    "请按账户状态做统计",
                ],
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
        self.assertEqual(result["data"]["analysis_mode"], "pandas_fallback")
        self.assertEqual(result["data"]["analysis"]["focus_column"], "账户状态")
        self.assertEqual(result["data"]["analysis"]["summary_title"], "账户状态分布分析")
        self.assertIn("### 账户状态统计", result["text"])
        self.assertEqual(result["data"]["analysis"]["distribution_rows"][0]["账户状态"], "正常")


if __name__ == "__main__":
    unittest.main()
