from __future__ import annotations

import json
import unittest

from backend.agent.skill_history import (
    build_combined_observation,
    get_skill_executions,
    merge_results_for_finish,
    record_skill_execution,
)


def _comparison_result(cur: int, prev: int, text: str) -> dict:
    return {
        "kind": "table",
        "text": text,
        "data": {
            "rows": [{"区域": "华东", f"{cur}月": 100, f"{prev}月": 90}],
            "comparison_meta": {"year": 2026, "cur_month": cur, "prev_month": prev},
        },
        "chart_plan": {
            "chart_type": "bar",
            "dimension": "区域",
            "metrics": [f"{cur}月", f"{prev}月"],
        },
    }


class SkillHistoryTest(unittest.TestCase):
    def test_build_combined_observation_includes_both_periods(self) -> None:
        executions = [
            {
                "skill": "chatbi-comparison",
                "observation": json.dumps(
                    {"comparison_period": {"year": 2026, "cur_month": 2, "prev_month": 1}},
                    ensure_ascii=False,
                ),
                "step": 1,
            },
            {
                "skill": "chatbi-comparison",
                "observation": json.dumps(
                    {"comparison_period": {"year": 2026, "cur_month": 3, "prev_month": 2}},
                    ensure_ascii=False,
                ),
                "step": 2,
            },
        ]
        combined = build_combined_observation(executions)
        self.assertIn("第 1 次", combined)
        self.assertIn("第 2 次", combined)
        self.assertIn('"cur_month": 2', combined)
        self.assertIn('"cur_month": 3', combined)

    def test_record_and_get_skill_executions(self) -> None:
        sink: dict = {}
        record_skill_execution(sink, "chatbi-comparison", _comparison_result(2, 1, "1-2月"), 1)
        record_skill_execution(sink, "chatbi-comparison", _comparison_result(3, 2, "2-3月"), 2)
        executions = get_skill_executions(sink)
        self.assertEqual(len(executions), 2)
        self.assertEqual(sink["last_skill_name"], "chatbi-comparison")

    def test_merge_results_for_finish_prefers_finish_text(self) -> None:
        executions = get_skill_executions({})
        sink: dict = {}
        record_skill_execution(sink, "chatbi-comparison", _comparison_result(2, 1, "段一"), 1)
        record_skill_execution(sink, "chatbi-comparison", _comparison_result(3, 2, "段二"), 2)
        executions = get_skill_executions(sink)
        merged = merge_results_for_finish(
            executions,
            {"text": "汇总：含两段环比。"},
            "chatbi-comparison",
        )
        self.assertEqual(merged["text"], "汇总：含两段环比。")
        self.assertGreaterEqual(len(merged.get("charts") or []), 2)

    def test_merge_results_for_finish_concatenates_without_finish_text(self) -> None:
        sink: dict = {}
        record_skill_execution(sink, "chatbi-comparison", _comparison_result(2, 1, "华东增长"), 1)
        record_skill_execution(sink, "chatbi-comparison", _comparison_result(3, 2, "华南增长"), 2)
        merged = merge_results_for_finish(
            get_skill_executions(sink),
            {},
            "chatbi-comparison",
        )
        self.assertIn("华东增长", merged["text"])
        self.assertIn("华南增长", merged["text"])


if __name__ == "__main__":
    unittest.main()
