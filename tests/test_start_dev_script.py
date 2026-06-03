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
        (repo / "database").mkdir(parents=True, exist_ok=True)
        (repo / ".env.dev").write_text(
            "\n".join(
                [
                    "CHATBI_DB_HOST=127.0.0.1",
                    "CHATBI_DB_PORT=3306",
                    "CHATBI_DB_NAME=chatbi_demo",
                    "CHATBI_DB_USER=demo_user",
                    "CHATBI_DB_PASSWORD=demo_pass",
                    "CHATBI_SEED_USERS=admin:admin123:admin;demo:demo123:user",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        (repo / "database/init.sql").write_text("SELECT 1;\n", encoding="utf-8")
        script_source = ROOT / "scripts/start_dev.sh"
        target = repo / "scripts/start_dev.sh"
        target.write_text(script_source.read_text(encoding="utf-8"), encoding="utf-8")
        target.chmod(target.stat().st_mode | stat.S_IEXEC)

    def create_fake_mysql(self, repo: Path) -> Path:
        bin_dir = repo / "fake-bin"
        bin_dir.mkdir()
        executable = bin_dir / "mysql"
        executable.write_text(
            "#!/usr/bin/env bash\n"
            'echo "mysql $*" >> "$CHATBI_START_DEV_LOG"\n'
            'if [[ "$*" == *"SELECT 1 FROM app_user"* ]]; then exit 1; fi\n'
            "cat >/dev/null\n"
            "exit 0\n",
            encoding="utf-8",
            newline="\n",
        )
        executable.chmod(executable.stat().st_mode | stat.S_IEXEC)
        return bin_dir

    def test_db_only_initializes_local_mysql(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            self.create_minimal_repo(repo)
            bin_dir = self.create_fake_mysql(repo)
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
            self.assertIn("mysql --protocol=TCP -h 127.0.0.1 -P 3306 -u root", log)
            self.assertIn("-u demo_user -pdemo_pass chatbi_demo", log)
            self.assertIn("Importing database/init.sql", result.stdout)
            self.assertIn("Local dev MySQL is ready on 127.0.0.1:3306", result.stdout)

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
