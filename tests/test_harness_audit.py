from __future__ import annotations

import unittest
from unittest.mock import patch

from backend.agent.harness_audit import build_audit_report


class HarnessAuditTest(unittest.TestCase):
    def test_build_audit_report_flags_rejections_and_failures(self):
        events = [
            {
                "span_name": "agent.harness",
                "event_name": "schema_rejected",
                "payload": {"step": 1},
            },
            {
                "span_name": "agent.harness",
                "event_name": "action_authorized",
                "payload": {"step": 2},
            },
            {
                "span_name": "agent.harness",
                "event_name": "action_executing",
                "payload": {"step": 2, "skill": "chatbi-semantic-query"},
            },
            {
                "span_name": "agent.skill",
                "event_name": "failed",
                "payload": {"skill": "chatbi-semantic-query"},
            },
            {
                "span_name": "agent.runner",
                "event_name": "completed",
                "payload": {"exhausted": True},
            },
        ]
        with patch("backend.agent.harness_audit.list_trace_events", return_value=events):
            report = build_audit_report("t1")
        self.assertEqual(report["status"], "error")
        codes = {item["code"] for item in report["issues"]}
        self.assertIn("HARNESS_SCHEMA_REJECTED", codes)
        self.assertIn("SKILL_FAILED", codes)
        self.assertIn("STEP_EXHAUSTED", codes)

    def test_build_audit_report_ok_when_no_issues(self):
        events = [
            {
                "span_name": "agent.harness",
                "event_name": "action_authorized",
                "payload": {"step": 1},
            },
            {
                "span_name": "agent.harness",
                "event_name": "action_executing",
                "payload": {"step": 1, "skill": "chatbi-semantic-query"},
            },
            {
                "span_name": "agent.harness",
                "event_name": "observation_built",
                "payload": {"step": 1, "skill": "chatbi-semantic-query"},
            },
        ]
        with patch("backend.agent.harness_audit.list_trace_events", return_value=events):
            report = build_audit_report("t2")
        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["score"], 100)


if __name__ == "__main__":
    unittest.main()
