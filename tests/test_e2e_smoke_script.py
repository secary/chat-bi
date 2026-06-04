from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/e2e_smoke.py"
SPEC = importlib.util.spec_from_file_location("e2e_smoke", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)
RUNNER = sys.modules["scripts.e2e_runner"]
CASES_MODULE = sys.modules["scripts.e2e_cases"]


class E2ESmokeScriptTest(unittest.TestCase):
    def test_metric_explainer_case_is_registered(self):
        case_ids = {case.id for case in MODULE.CASES}

        self.assertIn("S6", case_ids)
        self.assertIn("smoke", MODULE.CASE_GROUPS)
        self.assertIn("upload", MODULE.CASE_GROUPS)

    def test_run_case_validates_expected_text(self):
        case = MODULE.Case(
            "T1",
            "文本断言",
            "测试",
            expect_skills=["demo-skill"],
            expect_text=["关键结论"],
        )

        def fake_events(*_args, **_kwargs):
            yield {"type": "thinking", "content": "正在执行 Skill「demo-skill」..."}
            yield {"type": "text", "content": "这里没有目标文本"}
            yield {"type": "done", "content": None}

        with mock.patch.object(MODULE, "_stream_events", fake_events):
            ok, errors = MODULE._run_case(case, "http://example.test", None, 1)

        self.assertFalse(ok)
        self.assertIn("text 事件中应出现 '关键结论'", errors)

    def test_resolve_token_adds_bearer_to_raw_token(self):
        args = mock.Mock(token="abc123", username=None, password=None)

        self.assertEqual(MODULE._resolve_token(args), "Bearer abc123")

    def test_resolve_token_logs_in_with_credentials(self):
        args = mock.Mock(
            token=None,
            username="admin",
            password="secret",
            url="http://example.test/api",
            timeout=3,
        )

        with mock.patch.object(MODULE, "_login_token", return_value="Bearer fresh") as login:
            token = MODULE._resolve_token(args)

        self.assertEqual(token, "Bearer fresh")
        login.assert_called_once_with("http://example.test/api", "admin", "secret", 3)

    def test_selected_cases_prefers_explicit_case_ids(self):
        cases, unknown = MODULE._selected_cases({"S4"}, {"smoke"})

        self.assertEqual([case.id for case in cases], ["S4"])
        self.assertEqual(unknown, [])

    def test_selected_cases_expands_groups(self):
        cases, unknown = MODULE._selected_cases(None, {"metadata"})

        self.assertEqual([case.id for case in cases], ["S4", "S6"])
        self.assertEqual(unknown, [])

    def test_upload_case_is_multi_step(self):
        case = next(case for case in MODULE.CASES if case.id == "U1")

        self.assertEqual(case.upload_file, "data/chatbi_sales.csv")
        self.assertEqual(len(case.steps), 2)
        self.assertTrue(case.steps[0].expect_analysis_proposal)
        self.assertTrue(case.steps[1].expect_dashboard_ready)

    def test_run_step_case_carries_proposal_in_history(self):
        case = MODULE.Case(
            "TU",
            "上传链路",
            "upload",
            upload_file="data/demo.csv",
            steps=[
                CASES_MODULE.CaseStep("先分析", expect_analysis_proposal=True),
                CASES_MODULE.CaseStep("采纳", expect_dashboard_ready=True),
            ],
        )
        calls = []

        def fake_collect(_base_url, message, _token, _timeout, history=None, uploads=None):
            calls.append({"message": message, "history": history or [], "uploads": uploads or []})
            if message == "先分析":
                return {
                    "thinking": "",
                    "text": "请采纳",
                    "chart": False,
                    "proposal": {"proposed_metrics": [{"id": "m1"}]},
                    "dashboard": False,
                    "done": True,
                }, []
            return {
                "thinking": "",
                "text": "已生成",
                "chart": True,
                "proposal": None,
                "dashboard": True,
                "done": True,
            }, []

        with mock.patch.object(RUNNER, "upload_file", return_value={"server_path": "/tmp/u.csv"}):
            with mock.patch.object(RUNNER, "collect_chat", side_effect=fake_collect):
                ok, errors = RUNNER.run_step_case(case, "http://example.test", "Bearer t", 1)

        self.assertTrue(ok, errors)
        self.assertEqual(calls[0]["uploads"], [{"server_path": "/tmp/u.csv"}])
        self.assertEqual(calls[1]["uploads"], [])
        self.assertIn("/tmp/u.csv", calls[1]["history"][0]["content"])
        self.assertEqual(
            calls[1]["history"][1]["analysisProposal"], {"proposed_metrics": [{"id": "m1"}]}
        )


if __name__ == "__main__":
    unittest.main()
