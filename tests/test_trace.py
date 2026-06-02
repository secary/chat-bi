from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from backend.config import Settings
from backend.trace import create_trace_database_sql, create_trace_log_table_sql

from skills._shared import trace as skill_trace


class TraceConfigTest(unittest.TestCase):
    def test_log_db_reuses_main_host_port_by_default(self) -> None:
        env = {
            "CHATBI_DB_HOST": "127.0.0.1",
            "CHATBI_DB_PORT": "3308",
            "CHATBI_DB_NAME": "chatbi_demo",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()

        self.assertEqual(settings.db_config["port"], "3308")
        self.assertEqual(settings.log_db_config["host"], "127.0.0.1")
        self.assertEqual(settings.log_db_config["port"], "3308")
        self.assertEqual(settings.log_db_config["database"], "chatbi_demo")

    def test_log_db_can_still_use_separate_local_port(self) -> None:
        env = {
            "CHATBI_DB_HOST": "127.0.0.1",
            "CHATBI_DB_PORT": "3308",
            "CHATBI_DB_NAME": "chatbi_demo",
            "CHATBI_LOG_DB_HOST": "127.0.0.1",
            "CHATBI_LOG_DB_PORT": "33067",
            "CHATBI_LOG_DB_NAME": "chatbi_local_logs",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()

        self.assertEqual(settings.log_db_config["port"], "33067")

    def test_backend_trace_uses_prefixed_log_table(self) -> None:
        self.assertIn("CREATE TABLE IF NOT EXISTS log", create_trace_log_table_sql())
        self.assertIn("`chatbi_demo`", create_trace_database_sql("chatbi_demo"))

    def test_skill_trace_uses_same_prefixed_log_table(self) -> None:
        self.assertIn("CREATE TABLE IF NOT EXISTS log", skill_trace._create_trace_table_sql())
        self.assertNotIn("chatbi_", skill_trace._create_trace_table_sql())


if __name__ == "__main__":
    unittest.main()
