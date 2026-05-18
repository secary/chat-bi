from __future__ import annotations

import threading
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from backend.agent.executor import run_script
from backend.agent.prompt_builder import SkillDoc


class ExecutorRunScriptTest(unittest.TestCase):
    def test_run_script_handles_large_stdout_without_blocking(self):
        with TemporaryDirectory() as tmp:
            skill_dir = Path(tmp) / "demo-skill"
            scripts_dir = skill_dir / "scripts"
            scripts_dir.mkdir(parents=True)
            script = scripts_dir / "emit_large_json.py"
            script.write_text(
                "\n".join(
                    [
                        "import json",
                        "rows = [{'idx': i, 'value': 'x' * 64} for i in range(5000)]",
                        "print(json.dumps({'kind': 'table', 'text': 'ok', 'data': {'rows': rows}}, ensure_ascii=False))",
                    ]
                ),
                encoding="utf-8",
            )
            skill = SkillDoc("demo-large-output", "test", "", skill_dir)

            result_holder: dict[str, object] = {}
            error_holder: list[BaseException] = []

            def target() -> None:
                try:
                    result_holder["result"] = run_script(skill, [])
                except BaseException as exc:  # pragma: no cover - assertion below surfaces it
                    error_holder.append(exc)

            thread = threading.Thread(target=target, daemon=True)
            thread.start()
            thread.join(timeout=5)

            self.assertFalse(thread.is_alive(), "run_script blocked on large stdout")
            self.assertEqual(error_holder, [])
            result = result_holder.get("result")
            self.assertIsInstance(result, dict)
            assert isinstance(result, dict)
            self.assertEqual(result.get("kind"), "table")
            rows = result.get("data", {}).get("rows", [])
            self.assertEqual(len(rows), 5000)
            self.assertEqual(rows[0]["idx"], 0)


if __name__ == "__main__":
    unittest.main()
