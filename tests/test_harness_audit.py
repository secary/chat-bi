from __future__ import annotations

import unittest
from unittest.mock import patch

from backend.agent.harness_audit import build_audit_report
from backend.agent.harness_events import log_harness_decision_content_audit
from backend.agent.harness_state import HarnessState


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

    def test_log_harness_decision_content_audit_emits_full_audit_payload(self):
        captured = {}
        state = HarnessState(trace_id="t-audit", user_text="给建议", max_steps=4)
        state.begin_step(2)
        audit = {
            "status": "warning",
            "issue_count": 2,
            "issues": [
                {
                    "code": "DECISION_ADVICE_TOO_GENERIC",
                    "level": "warning",
                    "message": "有 1 条建议表述偏泛，缺少明确对象或动作。",
                },
                {
                    "code": "DECISION_ADVICE_NOT_GROUNDED",
                    "level": "warning",
                    "message": "有 1 条建议依据里缺少明显的业务事实证据。",
                },
            ],
        }

        def fake_log_event(trace_id, span_name, event_name, message="", payload=None, level="INFO"):
            captured.update(
                {
                    "trace_id": trace_id,
                    "span_name": span_name,
                    "event_name": event_name,
                    "message": message,
                    "payload": payload or {},
                    "level": level,
                }
            )

        with patch("backend.agent.harness_events.log_event", side_effect=fake_log_event):
            log_harness_decision_content_audit(
                "t-audit",
                state,
                skill_name="chatbi-decision-advisor",
                audit=audit,
                agent_id="business_advisor",
            )

        self.assertEqual(captured["event_name"], "decision_content_audited")
        self.assertEqual(captured["level"], "WARN")
        self.assertEqual(captured["payload"]["audit_status"], "warning")
        self.assertEqual(captured["payload"]["issue_count"], 2)
        self.assertEqual(
            captured["payload"]["issue_codes"],
            ["DECISION_ADVICE_TOO_GENERIC", "DECISION_ADVICE_NOT_GROUNDED"],
        )
        self.assertEqual(captured["payload"]["agent_id"], "business_advisor")
        self.assertEqual(captured["payload"]["decision_content_audit"], audit)

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

    def test_build_audit_report_includes_llm_config_flow_and_failure(self):
        events = [
            {
                "span_name": "admin.llm_settings",
                "event_name": "viewed",
                "payload": {"effective_model": "openai/x"},
            },
            {
                "span_name": "admin.llm_settings",
                "event_name": "profile_probe_tested",
                "payload": {
                    "model": "openai/x",
                    "ok": False,
                    "message": "API Key 校验失败，请确认密钥是否完整、是否属于当前服务商。",
                },
            },
        ]
        with patch("backend.agent.harness_audit.list_trace_events", return_value=events):
            report = build_audit_report("t-llm")

        self.assertEqual(report["status"], "error")
        codes = {item["code"] for item in report["issues"]}
        self.assertIn("LLM_CONFIG_TEST_FAILED", codes)
        flows = {flow["flow_key"]: flow for flow in report["business_flows"]}
        self.assertEqual(flows["llm_config"]["status"], "error")
        self.assertIn("API Key 校验失败", flows["llm_config"]["summary"])

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

    def test_build_audit_report_includes_semantic_query_flow(self):
        events = [
            {
                "span_name": "agent.harness",
                "event_name": "action_executing",
                "payload": {
                    "step": 1,
                    "skill": "chatbi-semantic-query",
                },
            },
            {
                "span_name": "agent.harness",
                "event_name": "observation_built",
                "payload": {
                    "step": 1,
                    "skill": "chatbi-semantic-query",
                    "ok": True,
                    "row_count": 4,
                    "has_chart_plan": True,
                    "kpi_count": 1,
                    "plan_summary": {
                        "metric": "销售额",
                        "dimensions": ["区域"],
                        "time_filter": "`order_date` >= '2026-01-01'",
                        "order_by_metric_desc": True,
                        "limit": None,
                    },
                },
            },
            {
                "span_name": "agent.harness",
                "event_name": "finish_emitted",
                "payload": {"step": 1, "action": "finish"},
            },
        ]
        with patch("backend.agent.harness_audit.list_trace_events", return_value=events):
            report = build_audit_report("query-trace")
        flows = {item["flow_key"]: item for item in report["business_flows"]}
        query = flows["semantic_query"]
        self.assertEqual(query["status"], "completed")
        self.assertIn("图表或 KPI", query["summary"])
        step_map = {step["key"]: step for step in query["steps"]}
        self.assertEqual(step_map["semantic_match"]["status"], "completed")
        self.assertEqual(step_map["query_plan"]["status"], "completed")
        self.assertEqual(step_map["rows_ready"]["status"], "completed")
        self.assertEqual(step_map["visual_output"]["status"], "completed")

    def test_build_audit_report_flags_decision_content_risks(self):
        events = [
            {
                "span_name": "agent.harness",
                "event_name": "action_authorized",
                "payload": {"step": 1, "skill": "chatbi-decision-advisor"},
            },
            {
                "span_name": "agent.harness",
                "event_name": "observation_built",
                "payload": {
                    "step": 1,
                    "skill": "chatbi-decision-advisor",
                    "ok": True,
                    "decision_content_audit": {
                        "status": "warning",
                        "issue_count": 2,
                        "issues": [
                            {
                                "code": "DECISION_ADVICE_TOO_GENERIC",
                                "level": "warning",
                                "message": "有 1 条建议表述偏泛，缺少明确对象或动作。",
                            },
                            {
                                "code": "DECISION_ADVICE_NOT_GROUNDED",
                                "level": "warning",
                                "message": "有 1 条建议依据里缺少明显的业务事实证据。",
                            },
                        ],
                    },
                },
            },
            {
                "span_name": "agent.harness",
                "event_name": "finish_emitted",
                "payload": {"step": 1, "action": "finish"},
            },
        ]
        with patch("backend.agent.harness_audit.list_trace_events", return_value=events):
            report = build_audit_report("decision-trace")
        codes = {item["code"] for item in report["issues"]}
        self.assertIn("DECISION_ADVICE_TOO_GENERIC", codes)
        self.assertIn("DECISION_ADVICE_NOT_GROUNDED", codes)

    def test_build_audit_report_includes_decision_content_audit_flow(self):
        events = [
            {
                "span_name": "agent.harness",
                "event_name": "observation_built",
                "payload": {
                    "step": 1,
                    "skill": "chatbi-decision-advisor",
                    "ok": True,
                    "decision_content_audit": {
                        "status": "ok",
                        "issue_count": 0,
                        "issues": [],
                    },
                },
            },
            {
                "span_name": "agent.harness",
                "event_name": "finish_emitted",
                "payload": {"step": 1, "action": "finish"},
            },
        ]
        with patch("backend.agent.harness_audit.list_trace_events", return_value=events):
            report = build_audit_report("decision-audit-ok")
        flows = {item["flow_key"]: item for item in report["business_flows"]}
        audit = flows["decision_content_audit"]
        self.assertEqual(audit["status"], "completed")
        self.assertIn("未发现明显风险", audit["summary"])
        step_map = {step["key"]: step for step in audit["steps"]}
        self.assertEqual(step_map["facts_grounding"]["status"], "completed")
        self.assertEqual(step_map["advice_quality"]["status"], "completed")
        self.assertEqual(step_map["scope_consistency"]["status"], "completed")


if __name__ == "__main__":
    unittest.main()
