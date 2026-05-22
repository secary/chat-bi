from __future__ import annotations

import unittest
from unittest.mock import patch

from backend.trace_repo import list_recent_trace_ids


class TraceRepoTest(unittest.TestCase):
    def test_list_recent_trace_ids_filters_non_chat_traces(self):
        rows = [
            {
                "trace_id": "chat-trace",
                "last_seen": "2026-05-22 10:00:00",
                "event_count": 12,
            },
            {
                "trace_id": "agent-trace",
                "last_seen": "2026-05-22 09:59:00",
                "event_count": 4,
            },
        ]
        with patch("backend.trace_repo.log_fetch_all", return_value=rows) as mocked:
            result = list_recent_trace_ids(20)

        self.assertEqual(result[0]["trace_id"], "chat-trace")
        sql = mocked.call_args.args[0]
        self.assertIn("span_name = 'http.chat'", sql)
        self.assertIn("HAVING SUM(CASE", sql)


if __name__ == "__main__":
    unittest.main()
