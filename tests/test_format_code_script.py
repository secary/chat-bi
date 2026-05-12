from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/format_code.py"
SPEC = importlib.util.spec_from_file_location("format_code", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class FormatCodeScriptTest(unittest.TestCase):
    def test_python_executable_prefers_windows_venv_when_present(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            python_path = root / ".venv/Scripts/python.exe"
            python_path.parent.mkdir(parents=True)
            python_path.write_text("")
            with mock.patch.object(MODULE, "ROOT", root):
                with mock.patch.dict(MODULE.os.environ, {}, clear=True):
                    self.assertEqual(MODULE.python_executable(), str(python_path))

    def test_frontend_target_detection_uses_prefix_and_suffix(self):
        self.assertTrue(MODULE.is_frontend_target("frontend/src/App.tsx"))
        self.assertFalse(MODULE.is_frontend_target("backend/main.py"))
        self.assertFalse(MODULE.is_frontend_target("src/App.tsx"))

    def test_to_frontend_arg_strips_frontend_prefix(self):
        self.assertEqual(MODULE.to_frontend_arg("frontend/src/App.tsx"), "src/App.tsx")

    def test_existing_targets_skips_deleted_paths(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            existing = root / "backend/main.py"
            existing.parent.mkdir(parents=True)
            existing.write_text("print('ok')\n")
            with mock.patch.object(MODULE, "ROOT", root):
                kept = MODULE.existing_targets(["backend/main.py", "missing.py"])
            self.assertEqual(kept, ["backend/main.py"])


if __name__ == "__main__":
    unittest.main()
