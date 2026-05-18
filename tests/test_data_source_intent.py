"""Tests for per-turn data source intent (demo DB vs upload file)."""

from __future__ import annotations

import unittest

from backend.agent.data_source_intent import (
    DataSourceIntent,
    format_handoff_data_source_line,
    format_intent_context_block,
    resolve_data_source,
)


class TestDataSourceIntent(unittest.TestCase):
    def test_explicit_demo_db_after_upload_history(self):
        messages = [
            {
                "role": "user",
                "content": "请分析 /tmp/chatbi-uploads/sales.csv",
            },
            {
                "role": "assistant",
                "content": "已读取上传文件。",
            },
            {
                "role": "user",
                "content": (
                    "不考虑上传的文件，从数据库中查询。各区域 2026 年 1 月到 4 月的销售额排行"
                ),
            },
        ]
        self.assertEqual(resolve_data_source(messages), DataSourceIntent.DEMO_DATABASE)

    def test_upload_path_in_current_turn(self):
        messages = [
            {
                "role": "user",
                "content": "请分析 /tmp/chatbi-uploads/sales.csv 并画图",
            },
        ]
        self.assertEqual(resolve_data_source(messages), DataSourceIntent.UPLOAD_FILE)

    def test_typical_ranking_without_upload_cue(self):
        messages = [{"role": "user", "content": "各区域 2026 年 1 月到 4 月销售额排行"}]
        self.assertEqual(resolve_data_source(messages), DataSourceIntent.DEMO_DATABASE)

    def test_ambiguous_after_upload_vague_followup(self):
        messages = [
            {"role": "user", "content": "请分析 /tmp/chatbi-uploads/sales.csv"},
            {"role": "assistant", "content": "ok"},
            {"role": "user", "content": "帮我继续分析一下"},
        ]
        self.assertEqual(resolve_data_source(messages), DataSourceIntent.AMBIGUOUS)

    def test_manager_handoff_user_original(self):
        messages = [
            {
                "role": "user",
                "content": (
                    "【Manager 交办】\n查演示库\n\n"
                    "【用户原述】\n不考虑上传，从数据库查各区域销售额排行"
                ),
            },
        ]
        self.assertEqual(resolve_data_source(messages), DataSourceIntent.DEMO_DATABASE)

    def test_format_blocks(self):
        demo = format_intent_context_block(DataSourceIntent.DEMO_DATABASE)
        self.assertIn("演示业务库", demo)
        upload = format_intent_context_block(
            DataSourceIntent.UPLOAD_FILE, upload_path="/tmp/chatbi-uploads/x.csv"
        )
        self.assertIn("file-ingestion", upload)
        self.assertIn("x.csv", upload)
        line = format_handoff_data_source_line(DataSourceIntent.DEMO_DATABASE)
        self.assertIn("演示业务库", line)


if __name__ == "__main__":
    unittest.main()
