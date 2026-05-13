from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_tests.py"
SPEC = importlib.util.spec_from_file_location("run_tests", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class RunTestsScriptTest(unittest.TestCase):
    def test_module_suite_manifest_paths_exist(self):
        self.assertEqual(MODULE.missing_manifest_paths(), [])

    def test_all_python_tests_are_assigned_to_a_module_suite(self):
        self.assertEqual(MODULE.suite_coverage_gaps(), [])

    def test_all_discovers_python_tests(self):
        discovered = MODULE.discover_python_tests()

        self.assertIn("tests/test_run_tests_script.py", discovered)
        self.assertTrue(
            any(path != "tests/test_run_tests_script.py" for path in discovered),
            "discover_python_tests() should find at least one other test file",
        )

    def test_deduplicates_group_selection(self):
        tests = MODULE.tests_for_groups(["quick", "data-sources"])

        self.assertEqual(tests.count("tests/test_database_overview_skill.py"), 1)

    def test_python_executable_falls_back_to_current_interpreter(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with mock.patch.object(MODULE, "ROOT", Path(temp_dir)):
                with mock.patch.dict(os.environ, {}, clear=True):
                    self.assertEqual(MODULE.python_executable(), sys.executable)

    def test_python_executable_uses_configured_interpreter(self):
        with mock.patch.dict(os.environ, {"CHATBI_PYTHON": "/tmp/custom-python"}):
            self.assertEqual(MODULE.python_executable(), "/tmp/custom-python")


if __name__ == "__main__":
    unittest.main()
