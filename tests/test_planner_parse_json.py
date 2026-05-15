from __future__ import annotations

import json
import unittest

from backend.agent.planner import parse_json_object


class ParseJsonObjectTest(unittest.TestCase):
    def test_parses_clean_object(self) -> None:
        obj = parse_json_object('  {"action": "finish", "text": "ok"}  ')
        self.assertEqual(obj["action"], "finish")

    def test_tolerates_trailing_prose_after_object(self) -> None:
        """Models sometimes append text after a valid JSON object (JSONDecodeError: Extra data)."""
        raw = '{"thought": "x", "action": "call_skill", "skill": "chatbi-dashboard-orchestration", "skill_args": []} trailing'
        obj = parse_json_object(raw)
        self.assertEqual(obj["action"], "call_skill")
        self.assertEqual(obj["skill"], "chatbi-dashboard-orchestration")

    def test_fenced_json_block(self) -> None:
        raw = """```json
{"action": "finish", "text": "done"}
```
"""
        obj = parse_json_object(raw)
        self.assertEqual(obj["action"], "finish")

    def test_nested_braces_inside_fenced_json(self) -> None:
        """Non-greedy ```...``` regex used to truncate nested objects."""
        inner = json.dumps(
            {"action": "finish", "data": {"nested": {"a": 1}}},
            ensure_ascii=False,
        )
        raw = f"```json\n{inner}\n```"
        obj = parse_json_object(raw)
        self.assertEqual(obj["data"]["nested"]["a"], 1)

    def test_rejects_non_object_root(self) -> None:
        with self.assertRaises(ValueError):
            parse_json_object("[1, 2]")

    def test_empty_content_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            parse_json_object("")
        with self.assertRaises(ValueError):
            parse_json_object("   \n")


if __name__ == "__main__":
    unittest.main()
