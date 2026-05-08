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


class E2ESmokeScriptTest(unittest.TestCase):
    def test_metric_explainer_case_is_registered(self):
        case_ids = {case.id for case in MODULE.CASES}

        self.assertIn("S6", case_ids)

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


if __name__ == "__main__":
    unittest.main()
