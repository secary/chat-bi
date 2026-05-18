from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from backend.agent.executor import run_script
from backend.agent.prompt_builder import SkillDoc


class ExecutorRunScriptTest(unittest.TestCase):
    def test_run_script_calls_python_api_without_subprocess(self):
        with TemporaryDirectory() as tmp:
            skill_dir = Path(tmp) / "demo-skill"
            scripts_dir = skill_dir / "scripts"
            scripts_dir.mkdir(parents=True)
            api_file = skill_dir / "api.py"
            api_file.write_text(
                "\n".join(
                    [
                        "def run(argv=None, context=None):",
                        "    rows = [{'idx': i, 'value': 'x' * 64} for i in range(5000)]",
                        "    return {'kind': 'table', 'text': 'ok', 'data': {'rows': rows}}",
                    ]
                ),
                encoding="utf-8",
            )
            script = scripts_dir / "emit_large_json.py"
            script.write_text("# legacy script placeholder\n", encoding="utf-8")
            skill = SkillDoc("demo-large-output", "test", "", skill_dir)

            with patch("subprocess.Popen") as mock_popen:
                result = run_script(skill, [])

            mock_popen.assert_not_called()
            self.assertIsInstance(result, dict)
            self.assertEqual(result.get("kind"), "table")
            rows = result.get("data", {}).get("rows", [])
            self.assertEqual(len(rows), 2000)
            self.assertEqual(rows[0]["idx"], 0)
            self.assertTrue(result.get("data", {}).get("result_truncated"))
            self.assertEqual(result.get("data", {}).get("original_row_count"), 5000)


if __name__ == "__main__":
    unittest.main()
