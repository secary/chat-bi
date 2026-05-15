from __future__ import annotations

import unittest
from pathlib import Path

from backend.agent.prompt_builder import SkillDoc
from backend.agent.skill_call_validator import (
    dialogue_text_from_messages,
    validate_skill_call,
    validation_observation_payload,
)
from backend.agent.upload_path_detect import has_upload_file_reference


def _doc(slug: str, **kwargs) -> SkillDoc:
    return SkillDoc(
        slug,
        "desc",
        "body",
        Path(f"/tmp/{slug}"),
        **kwargs,
    )


class SkillCallValidatorTest(unittest.TestCase):
    def test_upload_path_detect(self):
        self.assertTrue(has_upload_file_reference("/tmp/chatbi-uploads/a.csv"))
        self.assertFalse(has_upload_file_reference("各区域销售额"))

    def test_allowed_slugs_rejects_unknown(self):
        doc = _doc("chatbi-semantic-query")
        result = validate_skill_call(
            doc,
            allowed_slugs={"chatbi-database-overview"},
            dialogue_text="",
            last_result=None,
            user_text="有哪些表",
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.rule, "allowed_slugs")

    def test_no_upload_path_in_thread(self):
        doc = _doc(
            "chatbi-semantic-query",
            validator_requires=["no_upload_path_in_thread"],
        )
        blob = "请分析 /tmp/chatbi-uploads/sales.csv"
        result = validate_skill_call(
            doc,
            allowed_slugs={"chatbi-semantic-query"},
            dialogue_text=blob,
            last_result=None,
            user_text=blob,
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.rule, "no_upload_path_in_thread")

    def test_prior_observation_required(self):
        doc = _doc(
            "chatbi-chart-recommendation",
            validator_requires=["prior_observation"],
        )
        result = validate_skill_call(
            doc,
            allowed_slugs={"chatbi-chart-recommendation"},
            dialogue_text="推荐图表",
            last_result=None,
            user_text="推荐图表",
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.rule, "prior_observation")

        ok = validate_skill_call(
            doc,
            allowed_slugs={"chatbi-chart-recommendation"},
            dialogue_text="推荐图表",
            last_result={"data": {"rows": [{"a": 1}]}},
            user_text="推荐图表",
        )
        self.assertTrue(ok.ok)

    def test_upload_path_or_rows(self):
        doc = _doc(
            "chatbi-auto-analysis",
            validator_requires=["upload_path_or_rows"],
        )
        fail = validate_skill_call(
            doc,
            allowed_slugs={"chatbi-auto-analysis"},
            dialogue_text="生成看板",
            last_result=None,
            user_text="生成看板",
        )
        self.assertFalse(fail.ok)

        ok_path = validate_skill_call(
            doc,
            allowed_slugs={"chatbi-auto-analysis"},
            dialogue_text="/tmp/chatbi-uploads/x.csv",
            last_result=None,
            user_text="生成看板",
        )
        self.assertTrue(ok_path.ok)

    def test_validation_observation_payload_json(self):
        from backend.agent.skill_call_validator import ValidationResult

        payload = validation_observation_payload(
            "chatbi-chart-recommendation",
            ValidationResult(ok=False, reason="缺数据", rule="prior_observation"),
            {"chatbi-chart-recommendation"},
        )
        self.assertIn("skill_validation_rejected", payload)
        self.assertIn("prior_observation", payload)

    def test_dialogue_text_from_messages(self):
        text = dialogue_text_from_messages(
            [
                {"role": "user", "content": "你好"},
                {"role": "assistant", "content": "在的"},
            ]
        )
        self.assertIn("你好", text)
        self.assertIn("在的", text)
