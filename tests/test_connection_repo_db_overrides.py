from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from backend.agent.skill_runtime import SkillContext, activated_skill_env
from backend.connection_repo import skill_db_config_from_row


class ConnectionRepoDbOverridesTest(unittest.TestCase):
    def test_row_maps_to_internal_db_override_keys(self) -> None:
        out = skill_db_config_from_row(
            {
                "host": "host.docker.internal",
                "port": 3306,
                "username": "janus",
                "password": "secret",
                "database_name": "exchange",
            }
        )
        self.assertEqual(
            out,
            {
                "host": "host.docker.internal",
                "port": "3306",
                "user": "janus",
                "password": "secret",
                "database": "exchange",
            },
        )

    def test_skill_context_exports_overrides_to_chatbi_env(self) -> None:
        ctx = SkillContext(
            db_overrides={
                "host": "host.docker.internal",
                "port": "3306",
                "user": "janus",
                "password": "secret",
                "database": "exchange",
            }
        )
        with patch.dict(os.environ, {}, clear=True):
            with activated_skill_env(ctx):
                self.assertEqual(os.environ["CHATBI_DB_HOST"], "host.docker.internal")
                self.assertEqual(os.environ["CHATBI_DB_PORT"], "3306")
                self.assertEqual(os.environ["CHATBI_DB_USER"], "janus")
                self.assertEqual(os.environ["CHATBI_DB_NAME"], "exchange")


if __name__ == "__main__":
    unittest.main()
