from __future__ import annotations

import unittest

from backend.config import settings
from backend.trace import _payload_json, create_trace_log_table_sql, create_trace_table_sql


class TraceLoggingTest(unittest.TestCase):
    def test_trace_schema_uses_separate_database(self):
        self.assertIn("CREATE DATABASE IF NOT EXISTS", create_trace_table_sql())
        self.assertIn("CREATE TABLE IF NOT EXISTS chatbi_trace_log", create_trace_log_table_sql())

    def test_payload_is_truncated(self):
        payload = _payload_json({"text": "x" * 7000})
        self.assertIn("truncated", payload)

    def test_log_db_config_defaults_to_business_connection(self):
        self.assertEqual(settings.log_db_config["host"], settings.db_config["host"])
        self.assertEqual(settings.log_db_config["database"], "chatbi_logs")


if __name__ == "__main__":
    unittest.main()
