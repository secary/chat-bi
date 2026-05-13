from __future__ import annotations

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
        (repo / ".env.dev").write_text("CHATBI_DB_PORT=3308\n", encoding="utf-8")
        (repo / "scripts/format_code.py").write_text(
            "print('format placeholder')\n", encoding="utf-8"
        )
        bootstrap_source = ROOT / "scripts/bootstrap_dev.sh"
        (repo / "scripts/bootstrap_dev.sh").write_text(
            bootstrap_source.read_text(encoding="utf-8"),
            encoding="utf-8",
            newline="\n",
        )
        (repo / "scripts/bootstrap_dev.sh").chmod(
            (repo / "scripts/bootstrap_dev.sh").stat().st_mode | stat.S_IEXEC
        )

    def test_bootstrap_configures_hooks_without_formatting_by_default(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            self.create_minimal_repo(repo)
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, text=True)

            python_bin = repo / ".venv/bin/python"
            python_bin.parent.mkdir(parents=True, exist_ok=True)
            python_bin.write_text(
                "#!/usr/bin/env bash\n" 'echo "$@" > chatbi-bootstrap-format.log\n',
                encoding="utf-8",
                newline="\n",
            )
            python_bin.chmod(python_bin.stat().st_mode | stat.S_IEXEC)

            frontend_modules = repo / "frontend/node_modules"
            frontend_modules.mkdir(parents=True, exist_ok=True)

            result = subprocess.run(
                ["bash", "scripts/bootstrap_dev.sh"],
                cwd=repo,
                check=True,
                capture_output=True,
                text=True,
            )

            hook_path = subprocess.run(
                ["git", "config", "--get", "core.hooksPath"],
                cwd=repo,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            self.assertEqual(hook_path, ".githooks")

            log_file = repo / "chatbi-bootstrap-format.log"
            self.assertFalse(log_file.exists())
            self.assertIn("Skipping formatter.", result.stdout)
            self.assertIn("[bootstrap] .env.dev found", result.stdout)
            self.assertIn("[bootstrap] frontend/node_modules found", result.stdout)
            self.assertIn(
                "Quick tests: PYTHONPATH=. .venv/bin/python scripts/run_tests.py foundation -- -q",
                result.stdout,
            )
            self.assertNotIn("INSERT INTO", result.stdout)

    def test_bootstrap_runs_formatter_with_format_flag(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            self.create_minimal_repo(repo)
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, text=True)

            python_bin = repo / ".venv/bin/python"
            python_bin.parent.mkdir(parents=True, exist_ok=True)
            python_bin.write_text(
                "#!/usr/bin/env bash\n" 'echo "$@" > chatbi-bootstrap-format.log\n',
                encoding="utf-8",
                newline="\n",
            )
            python_bin.chmod(python_bin.stat().st_mode | stat.S_IEXEC)

            result = subprocess.run(
                ["bash", "scripts/bootstrap_dev.sh", "--format"],
                cwd=repo,
                check=True,
                capture_output=True,
                text=True,
            )

            log_file = repo / "chatbi-bootstrap-format.log"
            self.assertTrue(log_file.is_file())
            self.assertIn("scripts/format_code.py", log_file.read_text(encoding="utf-8"))
            self.assertIn("Running formatter with", result.stdout)

    def test_bootstrap_warns_when_env_or_node_modules_missing(self):
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

            self.assertIn("Skipping formatter.", result.stdout)
            self.assertIn(".env.dev not found.", result.stdout)
            self.assertIn(
                "frontend/node_modules missing. Run: cd frontend && npm ci", result.stdout
            )

    def test_bootstrap_sync_runs_uv_and_npm_when_available(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            self.create_minimal_repo(repo)
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, text=True)
            (repo / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
            (repo / "frontend/package-lock.json").write_text("{}", encoding="utf-8")

            bin_dir = repo / "fake-bin"
            bin_dir.mkdir()
            for name in ("uv", "npm"):
                executable = bin_dir / name
                executable.write_text(
                    "#!/usr/bin/env bash\n" f'echo {name} "$@" >> "$BOOTSTRAP_SYNC_LOG"\n',
                    encoding="utf-8",
                    newline="\n",
                )
                executable.chmod(executable.stat().st_mode | stat.S_IEXEC)

            sync_log_path = repo / "bootstrap-sync.log"
            result = subprocess.run(
                ["bash", "scripts/bootstrap_dev.sh", "--sync"],
                cwd=repo,
                check=True,
                capture_output=True,
                text=True,
                env={
                    "BOOTSTRAP_SYNC_LOG": str(sync_log_path),
                    "PATH": f"{bin_dir}:{'/usr/bin:/bin'}",
                },
            )

            sync_log = sync_log_path.read_text(encoding="utf-8")
            self.assertIn("uv sync", sync_log)
            self.assertIn("npm ci", sync_log)
            self.assertIn("Syncing Python environment with uv", result.stdout)
            self.assertIn("Syncing frontend dependencies with npm ci", result.stdout)
