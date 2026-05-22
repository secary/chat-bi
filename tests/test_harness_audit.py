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
            {
                "span_name": "agent.harness",
                "event_name": "finish_emitted",
                "payload": {"step": 1, "action": "finish"},
            },
        ]
        with patch("backend.agent.harness_audit.list_trace_events", return_value=events):
            report = build_audit_report("t2")
        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["score"], 100)

    def test_build_audit_report_flags_missing_finish(self):
        events = [
            {
                "span_name": "agent.harness",
                "event_name": "action_authorized",
                "payload": {"step": 1, "action": "delegate_tasks", "mode": "multi"},
            },
            {
                "span_name": "agent.harness",
                "event_name": "action_executing",
                "payload": {
                    "step": 1,
                    "task_index": 0,
                    "skill": "specialist:demo_query",
                    "mode": "multi",
                },
            },
            {
                "span_name": "agent.harness",
                "event_name": "observation_built",
                "payload": {"step": 1, "task_index": 0, "mode": "multi"},
            },
        ]
        with patch("backend.agent.harness_audit.list_trace_events", return_value=events):
            report = build_audit_report("t3")
        self.assertEqual(report["status"], "warning")
        codes = {item["code"] for item in report["issues"]}
        self.assertIn("MISSING_FINISH_EVENT", codes)

    def test_build_audit_report_flags_empty_specialist_outcome(self):
        events = [
            {
                "span_name": "agent.harness",
                "event_name": "action_authorized",
                "payload": {"step": 1, "action": "delegate_tasks", "mode": "multi"},
            },
            {
                "span_name": "agent.harness",
                "event_name": "action_executing",
                "payload": {
                    "step": 1,
                    "task_index": 0,
                    "skill": "specialist:demo_query",
                    "mode": "multi",
                },
            },
            {
                "span_name": "agent.harness",
                "event_name": "observation_built",
                "payload": {
                    "step": 1,
                    "task_index": 0,
                    "action": "run_specialist",
                    "agent_id": "demo_query",
                    "ok": True,
                    "has_result": False,
                    "observation_preview": "（无工具结果）",
                },
            },
            {
                "span_name": "agent.harness",
                "event_name": "finish_emitted",
                "payload": {"step": 1, "action": "finish"},
            },
        ]
        with patch("backend.agent.harness_audit.list_trace_events", return_value=events):
            report = build_audit_report("t4")
        codes = {item["code"] for item in report["issues"]}
        self.assertIn("EMPTY_SPECIALIST_OUTCOME", codes)

    def test_build_audit_report_flags_summary_with_unmet_dependency(self):
        events = [
            {
                "span_name": "agent.harness",
                "event_name": "action_authorized",
                "payload": {"step": 1, "action": "delegate_tasks", "mode": "multi"},
            },
            {
                "span_name": "agent.harness",
                "event_name": "observation_built",
                "payload": {
                    "step": 1,
                    "task_index": 1,
                    "action": "run_specialist",
                    "agent_id": "business_advisor",
                    "ok": False,
                    "has_result": False,
                    "dependency_warning": "缺少已采纳指标的具体数值，无法生成建议",
                    "observation_preview": "缺少已采纳指标的具体数值，无法生成建议",
                },
            },
            {
                "span_name": "agent.harness",
                "event_name": "summary_dependency_unmet",
                "payload": {
                    "step": 1,
                    "action": "finish",
                    "warning_count": 1,
                    "warnings": ["经营决策建议: 缺少已采纳指标的具体数值，无法生成建议"],
                },
            },
            {
                "span_name": "agent.harness",
                "event_name": "finish_emitted",
                "payload": {"step": 1, "action": "finish"},
            },
        ]
        with patch("backend.agent.harness_audit.list_trace_events", return_value=events):
            report = build_audit_report("t5")
        codes = {item["code"] for item in report["issues"]}
        self.assertIn("DOWNSTREAM_DATA_MISSING", codes)
        self.assertIn("SUMMARY_WITH_UNMET_DEPENDENCY", codes)

    def test_build_audit_report_includes_upload_analysis_flow(self):
        events = [
            {
                "span_name": "agent.harness",
                "event_name": "action_executing",
                "payload": {
                    "step": 1,
                    "skill": "chatbi-file-ingestion",
                },
            },
            {
                "span_name": "agent.harness",
                "event_name": "observation_built",
                "payload": {
                    "step": 1,
                    "skill": "chatbi-file-ingestion",
                    "ok": True,
                    "analysis_mode": "schema_validated",
                    "row_count": 12,
                    "has_rows": True,
                },
            },
            {
                "span_name": "agent.harness",
                "event_name": "action_executing",
                "payload": {
                    "step": 2,
                    "skill": "chatbi-auto-analysis",
                },
            },
            {
                "span_name": "agent.harness",
                "event_name": "observation_built",
                "payload": {
                    "step": 2,
                    "skill": "chatbi-auto-analysis",
                    "ok": True,
                    "status": "ready",
                    "has_auto_analysis": True,
                    "dashboard_ready": True,
                },
            },
            {
                "span_name": "agent.harness",
                "event_name": "finish_emitted",
                "payload": {"step": 2, "action": "finish"},
            },
        ]
        with patch("backend.agent.harness_audit.list_trace_events", return_value=events):
            report = build_audit_report("upload-trace")
        flows = {item["flow_key"]: item for item in report["business_flows"]}
        upload = flows["upload_analysis"]
        self.assertEqual(upload["status"], "completed")
        self.assertIn("看板结果已就绪", upload["summary"])
        step_map = {step["key"]: step for step in upload["steps"]}
        self.assertEqual(step_map["file_ingestion"]["status"], "completed")
        self.assertEqual(step_map["schema_validation"]["status"], "completed")
        self.assertEqual(step_map["auto_analysis"]["status"], "completed")
        self.assertEqual(step_map["dashboard_generation"]["status"], "completed")


if __name__ == "__main__":
    unittest.main()
