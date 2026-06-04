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
        (repo / "database/init.sql").write_text(
            "CREATE DATABASE IF NOT EXISTS chatbi_demo;\n" "USE chatbi_demo;\n" "SELECT 1;\n",
            encoding="utf-8",
        )
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
            'if [[ "$*" == *"information_schema.TABLES"* ]]; then\n'
            '  echo "${CHATBI_FAKE_TABLE_COUNT:-0}"\n'
            "  exit 0\n"
            "fi\n"
            'if [[ -n "${CHATBI_START_DEV_SQL_LOG:-}" ]]; then\n'
            '  cat >> "$CHATBI_START_DEV_SQL_LOG"\n'
            "else\n"
            "cat >/dev/null\n"
            "fi\n"
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

    def test_db_only_imports_init_sql_into_configured_database(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            self.create_minimal_repo(repo)
            env_path = repo / ".env.dev"
            env_path.write_text(
                env_path.read_text(encoding="utf-8").replace(
                    "CHATBI_DB_NAME=chatbi_demo",
                    "CHATBI_DB_NAME=chatbi_dev",
                ),
                encoding="utf-8",
            )
            bin_dir = self.create_fake_mysql(repo)
            log_path = repo / "start-dev.log"
            sql_log_path = repo / "start-dev.sql"

            subprocess.run(
                ["bash", "scripts/start_dev.sh", "--db-only"],
                cwd=repo,
                check=True,
                capture_output=True,
                text=True,
                env={
                    "CHATBI_START_DEV_LOG": str(log_path),
                    "CHATBI_START_DEV_SQL_LOG": str(sql_log_path),
                    "PATH": f"{bin_dir}:{'/usr/bin:/bin'}",
                },
            )

            sql_log = sql_log_path.read_text(encoding="utf-8")
            self.assertIn("CREATE DATABASE IF NOT EXISTS chatbi_dev", sql_log)
            self.assertIn("USE chatbi_dev", sql_log)
            self.assertNotIn("USE chatbi_demo;", sql_log)

    def test_db_only_skips_init_sql_when_database_has_tables(self) -> None:
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
                    "CHATBI_FAKE_TABLE_COUNT": "1",
                    "CHATBI_START_DEV_LOG": str(log_path),
                    "PATH": f"{bin_dir}:{'/usr/bin:/bin'}",
                },
            )

            self.assertNotIn("Importing database/init.sql", result.stdout)
            self.assertIn("skipping database/init.sql", result.stdout)
            self.assertIn("Local dev MySQL is ready on 127.0.0.1:3306", result.stdout)

    def test_db_only_loads_env_database_connections(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            self.create_minimal_repo(repo)
            env_path = repo / ".env.dev"
            env_path.write_text(
                env_path.read_text(encoding="utf-8")
                + "\n".join(
                    [
                        "CHATBI_DB_CONNECTION_1_NAME=业务库一",
                        "CHATBI_DB_CONNECTION_1_HOST=127.0.0.1",
                        "CHATBI_DB_CONNECTION_1_PORT=3306",
                        "CHATBI_DB_CONNECTION_1_USER=demo_user",
                        "CHATBI_DB_CONNECTION_1_PASSWORD=demo_pass",
                        "CHATBI_DB_CONNECTION_1_DATABASE=chatbi_demo",
                        "CHATBI_DB_CONNECTION_1_DEFAULT=true",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            bin_dir = self.create_fake_mysql(repo)
            log_path = repo / "start-dev.log"
            sql_log_path = repo / "start-dev.sql"

            result = subprocess.run(
                ["bash", "scripts/start_dev.sh", "--db-only"],
                cwd=repo,
                check=True,
                capture_output=True,
                text=True,
                env={
                    "CHATBI_FAKE_TABLE_COUNT": "1",
                    "CHATBI_START_DEV_LOG": str(log_path),
                    "CHATBI_START_DEV_SQL_LOG": str(sql_log_path),
                    "PATH": f"{bin_dir}:{'/usr/bin:/bin'}",
                },
            )

            log = log_path.read_text(encoding="utf-8")
            sql_log = sql_log_path.read_text(encoding="utf-8")
            self.assertIn("UPDATE admin_db_connection SET is_default = 0", log)
            self.assertIn("INSERT INTO admin_db_connection", sql_log)
            self.assertIn("'业务库一'", sql_log)
            self.assertIn("'chatbi_demo'", sql_log)
            self.assertIn("Loaded env database connection: 业务库一", result.stdout)

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

    def test_requires_env_dev(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            self.create_minimal_repo(repo)
            (repo / ".env.dev").unlink()

            result = subprocess.run(
                ["bash", "scripts/start_dev.sh", "--db-only"],
                cwd=repo,
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn("Missing", result.stderr)
            self.assertIn(".env.dev", result.stderr)
