"""Session message UI payload merge (dashboard / proposal replay)."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from backend.session_repo import load_messages_ui


class SessionRepoPayloadUiTest(unittest.TestCase):
    def test_load_messages_ui_merges_dashboard_ready(self) -> None:
        fake_rows = [
            {
                "id": 1,
                "role": "assistant",
                "content": "看板说明",
                "payload_json": {
                    "thinking": ["t1"],
                    "dashboardReady": {"title": "上传看板", "widgets": [{"id": "a"}]},
                },
            }
        ]
        with patch("backend.session_repo.app_fetch_all", return_value=fake_rows):
            out = load_messages_ui(42)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["content"], "看板说明")
        self.assertIn("dashboardReady", out[0])
        self.assertEqual(out[0]["dashboardReady"]["title"], "上传看板")
        self.assertEqual(len(out[0]["dashboardReady"]["widgets"]), 1)

    def test_load_messages_ui_merges_plan_summary_and_proposal(self) -> None:
        fake_rows = [
            {
                "id": 2,
                "role": "assistant",
                "content": "正文",
                "payload_json": {
                    "planSummary": {"steps": []},
                    "analysisProposal": {"markdown": "x", "proposed_metrics": []},
                },
            }
        ]
        with patch("backend.session_repo.app_fetch_all", return_value=fake_rows):
            out = load_messages_ui(99)
        self.assertIn("planSummary", out[0])
        self.assertIn("analysisProposal", out[0])


if __name__ == "__main__":
    unittest.main()
