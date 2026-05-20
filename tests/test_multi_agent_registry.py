"""Registry + slug filtering for multi-agent skills."""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from backend.agent.multi_agent_registry import (
    list_all_registry_agent_ids,
    list_registry_agent_ids,
    preferred_skill_slugs_for_agent,
    skills_for_agent,
    write_registry_dict,
)
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

    def test_dynamic_mode_prefers_configured_skills_but_keeps_runtime_flexible(self) -> None:
        reg_file = Path(self.id().replace(".", "_")).with_suffix(".yaml")

        def _path() -> Path:
            return Path("/tmp") / reg_file

        with patch("backend.agent.multi_agent_registry._registry_path", _path):
            write_registry_dict(
                {
                    "agents": {
                        "flex": {
                            "label": "灵活专线",
                            "role_prompt": "",
                            "skill_mode": "dynamic",
                            "skills": ["chatbi-semantic-query"],
                            "blocked_skills": ["chatbi-comparison"],
                        }
                    }
                }
            )
            preferred = preferred_skill_slugs_for_agent("flex")
            docs = skills_for_agent("flex")
        names = [d.skill_dir.name for d in docs]
        self.assertEqual(preferred, ["chatbi-semantic-query"])
        self.assertTrue(names)
        self.assertEqual(names[0], "chatbi-semantic-query")
        self.assertNotIn("chatbi-comparison", names)

    def test_restricted_mode_only_allows_configured_skills(self) -> None:
        reg_file = Path(self.id().replace(".", "_")).with_suffix(".yaml")

        def _path() -> Path:
            return Path("/tmp") / reg_file

        with patch("backend.agent.multi_agent_registry._registry_path", _path):
            write_registry_dict(
                {
                    "agents": {
                        "strict": {
                            "label": "严格专线",
                            "role_prompt": "",
                            "skill_mode": "restricted",
                            "skills": ["chatbi-semantic-query", "chatbi-comparison"],
                            "blocked_skills": ["chatbi-comparison"],
                        }
                    }
                }
            )
            docs = skills_for_agent("strict")
        names = [d.skill_dir.name for d in docs]
        self.assertEqual(names, ["chatbi-semantic-query"])

    def test_disabled_agent_is_hidden_from_runtime_list(self) -> None:
        reg_file = Path(self.id().replace(".", "_")).with_suffix(".yaml")

        def _path() -> Path:
            return Path("/tmp") / reg_file

        with patch("backend.agent.multi_agent_registry._registry_path", _path):
            write_registry_dict(
                {
                    "agents": {
                        "enabled_agent": {"enabled": True, "label": "A", "skills": []},
                        "disabled_agent": {"enabled": False, "label": "B", "skills": []},
                    }
                }
            )
            runtime_ids = list_registry_agent_ids()
            all_ids = list_all_registry_agent_ids()
        self.assertEqual(runtime_ids, ["enabled_agent"])
        self.assertEqual(all_ids, ["enabled_agent", "disabled_agent"])


if __name__ == "__main__":
    unittest.main()
