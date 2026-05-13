from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from backend.config import Settings


class ConfigDbDefaultsTest(unittest.TestCase):
    def test_feature_db_names_default_to_main_db(self) -> None:
        env = {
            "CHATBI_DB_HOST": "127.0.0.1",
            "CHATBI_DB_PORT": "3308",
            "CHATBI_DB_USER": "demo_user",
            "CHATBI_DB_PASSWORD": "demo_pass",
            "CHATBI_DB_NAME": "chatbi_demo",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()
        self.assertEqual(settings.app_db_name, "chatbi_demo")
        self.assertEqual(settings.admin_db_name, "chatbi_demo")
        self.assertEqual(settings.log_db_name, "chatbi_demo")

    def test_explicit_feature_db_names_still_override_defaults(self) -> None:
        env = {
            "CHATBI_DB_NAME": "chatbi_demo",
            "CHATBI_APP_DB_NAME": "chatbi_app",
            "CHATBI_ADMIN_DB_NAME": "chatbi_admin",
            "CHATBI_LOG_DB_NAME": "chatbi_logs",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()
        self.assertEqual(settings.app_db_name, "chatbi_app")
        self.assertEqual(settings.admin_db_name, "chatbi_admin")
        self.assertEqual(settings.log_db_name, "chatbi_logs")
