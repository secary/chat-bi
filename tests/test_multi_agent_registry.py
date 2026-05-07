"""Registry + slug filtering for multi-agent skills."""

from __future__ import annotations

import unittest

from backend.agent.prompt_builder import scan_skills_for_slugs
from backend.config import settings


class MultiAgentRegistryTest(unittest.TestCase):
    def test_scan_skills_for_slugs_preserves_order_and_filters(self) -> None:
        docs = scan_skills_for_slugs(
            settings.skills_dir,
            ["chatbi-semantic-query", "nonexistent-slug", "chatbi-comparison"],
        )
        names = [d.skill_dir.name for d in docs]
        self.assertEqual(names, ["chatbi-semantic-query", "chatbi-comparison"])


if __name__ == "__main__":
    unittest.main()
