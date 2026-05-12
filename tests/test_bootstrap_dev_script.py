from __future__ import annotations

import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class BootstrapDevScriptTest(unittest.TestCase):
    def create_minimal_repo(self, repo: Path) -> None:
        (repo / "scripts").mkdir(parents=True, exist_ok=True)
        (repo / "frontend").mkdir(parents=True, exist_ok=True)
        (repo / ".githooks").mkdir(parents=True, exist_ok=True)
        (repo / "scripts/format_code.py").write_text(
            "print('format placeholder')\n", encoding="utf-8"
        )
        bootstrap_source = ROOT / "scripts/bootstrap_dev.sh"
        (repo / "scripts/bootstrap_dev.sh").write_text(
            bootstrap_source.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        (repo / "scripts/bootstrap_dev.sh").chmod(
            (repo / "scripts/bootstrap_dev.sh").stat().st_mode | stat.S_IEXEC
        )

    def test_bootstrap_configures_hooks_and_runs_formatter_when_venv_exists(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            self.create_minimal_repo(repo)
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, text=True)

            python_bin = repo / ".venv/bin/python"
            python_bin.parent.mkdir(parents=True, exist_ok=True)
            python_bin.write_text(
                "#!/usr/bin/env bash\n"
                'echo "$@" > "${TMPDIR:-/tmp}/chatbi-bootstrap-format.log"\n',
                encoding="utf-8",
            )
            python_bin.chmod(python_bin.stat().st_mode | stat.S_IEXEC)

            frontend_modules = repo / "frontend/node_modules"
            frontend_modules.mkdir(parents=True, exist_ok=True)

            env = os.environ.copy()
            env["TMPDIR"] = temp_dir
            result = subprocess.run(
                ["bash", "scripts/bootstrap_dev.sh"],
                cwd=repo,
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )

            hook_path = subprocess.run(
                ["git", "config", "--get", "core.hooksPath"],
                cwd=repo,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            self.assertEqual(hook_path, ".githooks")

            log_file = Path(temp_dir) / "chatbi-bootstrap-format.log"
            self.assertTrue(log_file.is_file())
            self.assertIn("scripts/format_code.py", log_file.read_text(encoding="utf-8"))
            self.assertIn("[bootstrap] .env.dev found", result.stdout)
            self.assertIn("[bootstrap] frontend/node_modules found", result.stdout)

    def test_bootstrap_warns_when_venv_or_node_modules_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            self.create_minimal_repo(repo)
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, text=True)

            env_dev = repo / ".env.dev"
            if env_dev.exists():
                env_dev.unlink()

            result = subprocess.run(
                ["bash", "scripts/bootstrap_dev.sh"],
                cwd=repo,
                check=True,
                capture_output=True,
                text=True,
            )

            self.assertIn(
                "Python virtualenv not found at .venv. Skipping formatter run.", result.stdout
            )
            self.assertIn(".env.dev not found.", result.stdout)
            self.assertIn(
                "frontend/node_modules missing. Run: cd frontend && npm ci", result.stdout
            )
