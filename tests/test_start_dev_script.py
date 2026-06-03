from __future__ import annotations

import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class StartDevScriptTest(unittest.TestCase):
    def create_minimal_repo(self, repo: Path) -> None:
        (repo / "scripts").mkdir(parents=True, exist_ok=True)
        (repo / "frontend").mkdir(parents=True, exist_ok=True)
        (repo / ".env.dev").write_text("CHATBI_DB_PORT=33067\n", encoding="utf-8")
        (repo / "docker-compose.dev.yml").write_text(
            "services:\n  chatbi-db-dev:\n    image: mysql:8.0\n",
            encoding="utf-8",
        )
        script_source = ROOT / "scripts/start_dev.sh"
        target = repo / "scripts/start_dev.sh"
        target.write_text(script_source.read_text(encoding="utf-8"), encoding="utf-8")
        target.chmod(target.stat().st_mode | stat.S_IEXEC)

    def create_fake_docker(self, repo: Path) -> Path:
        bin_dir = repo / "fake-bin"
        bin_dir.mkdir()
        executable = bin_dir / "docker"
        executable.write_text(
            "#!/usr/bin/env bash\n" 'echo "docker $*" >> "$CHATBI_START_DEV_LOG"\n' "exit 0\n",
            encoding="utf-8",
            newline="\n",
        )
        executable.chmod(executable.stat().st_mode | stat.S_IEXEC)
        return bin_dir

    def test_db_only_starts_dev_mysql_container(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            self.create_minimal_repo(repo)
            bin_dir = self.create_fake_docker(repo)
            log_path = repo / "start-dev.log"

            result = subprocess.run(
                ["bash", "scripts/start_dev.sh", "--db-only"],
                cwd=repo,
                check=True,
                capture_output=True,
                text=True,
                env={
                    "CHATBI_START_DEV_LOG": str(log_path),
                    "PATH": f"{bin_dir}:{'/usr/bin:/bin'}",
                },
            )

            log = log_path.read_text(encoding="utf-8")
            self.assertIn("docker compose --env-file", log)
            self.assertIn("docker-compose.dev.yml up -d chatbi-db-dev", log)
            self.assertIn("Dev MySQL is ready on 127.0.0.1:33067", result.stdout)

    def test_rejects_invalid_port(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            self.create_minimal_repo(repo)

            result = subprocess.run(
                ["bash", "scripts/start_dev.sh", "--backend-port", "nope"],
                cwd=repo,
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("Ports must be non-negative integers.", result.stderr)
