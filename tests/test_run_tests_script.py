from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


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
        self.assertIn("tests/test_database_overview_skill.py", discovered)

    def test_deduplicates_group_selection(self):
        tests = MODULE.tests_for_groups(["quick", "data-sources"])

        self.assertEqual(tests.count("tests/test_database_overview_skill.py"), 1)


if __name__ == "__main__":
    unittest.main()
