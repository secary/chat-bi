from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from backend.env_loader import load_project_env


class EnvLoaderTest(unittest.TestCase):
    def test_dev_env_overrides_base_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env").write_text("CHATBI_DB_PORT=3307\n", encoding="utf-8")
            (root / ".env.dev").write_text("CHATBI_DB_PORT=3308\n", encoding="utf-8")

            previous = os.environ.get("CHATBI_DB_PORT")
            os.environ.pop("CHATBI_DB_PORT", None)
            try:
                load_project_env(root)
                self.assertEqual(os.environ.get("CHATBI_DB_PORT"), "3308")
            finally:
                if previous is None:
                    os.environ.pop("CHATBI_DB_PORT", None)
                else:
                    os.environ["CHATBI_DB_PORT"] = previous


if __name__ == "__main__":
    unittest.main()
