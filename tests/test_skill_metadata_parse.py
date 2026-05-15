from __future__ import annotations

import unittest
from pathlib import Path

from backend.agent.prompt_builder import (
    SkillDoc,
    _skills_markdown_lines,
    parse_frontmatter,
    scan_skills,
)
from backend.config import settings


class SkillMetadataParseTest(unittest.TestCase):
    def test_yaml_frontmatter_lists(self):
        text = """---
name: demo-skill
description: Demo skill
trigger_conditions:
  - 用户问 A
when_not_to_use:
  - 用户问 B
required_context:
  - 需要 C
---

# Body
"""
        meta, body = parse_frontmatter(text)
        self.assertEqual(meta["name"], "demo-skill")
        self.assertEqual(meta["trigger_conditions"], ["用户问 A"])
        self.assertEqual(meta["when_not_to_use"], ["用户问 B"])
        self.assertEqual(meta["required_context"], ["需要 C"])
        self.assertIn("# Body", body)

    def test_legacy_single_line_frontmatter_fallback(self):
        text = """---
name: legacy
description: one line desc
---

Content
"""
        meta, body = parse_frontmatter(text)
        self.assertEqual(meta["name"], "legacy")
        self.assertEqual(meta["description"], "one line desc")
        self.assertIn("Content", body)

    def test_skills_markdown_includes_metadata_sections(self):
        doc = SkillDoc(
            "demo",
            "desc",
            "## Workflow\n1. step",
            Path("/tmp/demo"),
            trigger_conditions=["时机1"],
            when_not_to_use=["禁用1"],
            required_context=["上下文1"],
        )
        joined = "\n".join(_skills_markdown_lines([doc]))
        self.assertIn("**选用时机**", joined)
        self.assertIn("时机1", joined)
        self.assertIn("**不要用**", joined)
        self.assertIn("禁用1", joined)
        self.assertIn("**必备上下文**", joined)

    def test_scan_skills_loads_trigger_conditions_from_disk(self):
        docs = scan_skills(settings.skills_dir)
        by_slug = {d.skill_dir.name: d for d in docs}
        chart = by_slug.get("chatbi-chart-recommendation")
        self.assertIsNotNone(chart)
        assert chart is not None
        self.assertTrue(chart.trigger_conditions)
