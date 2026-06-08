from __future__ import annotations

import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class LaunchScriptTest(unittest.TestCase):
    def create_minimal_repo(self, repo: Path) -> None:
        (repo / "scripts").mkdir(parents=True, exist_ok=True)
        (repo / "docker-compose.yml").write_text(
            "services:\n  chatbi-app:\n    image: chatbi-test\n",
            encoding="utf-8",
        )
        (repo / ".env.example").write_text(
            "CHATBI_SEED_USERS=admin:admin123:admin\n",
            encoding="utf-8",
        )
        script_source = ROOT / "scripts/launch.sh"
        target = repo / "scripts/launch.sh"
        target.write_text(script_source.read_text(encoding="utf-8"), encoding="utf-8")
        target.chmod(target.stat().st_mode | stat.S_IEXEC)

    def create_fake_bin(self, repo: Path) -> Path:
        bin_dir = repo / "fake-bin"
        bin_dir.mkdir()
        docker = bin_dir / "docker"
        docker.write_text(
            "#!/usr/bin/env bash\n" 'echo "docker $*" >> "$START_PROD_LOG"\n' "exit 0\n",
            encoding="utf-8",
            newline="\n",
        )
        docker.chmod(docker.stat().st_mode | stat.S_IEXEC)

        for name in ("curl", "open"):
            executable = bin_dir / name
            executable.write_text(
                "#!/usr/bin/env bash\n" f'echo "{name} $*" >> "$START_PROD_LOG"\n' "exit 0\n",
                encoding="utf-8",
                newline="\n",
            )
            executable.chmod(executable.stat().st_mode | stat.S_IEXEC)
        return bin_dir

    def test_launch_builds_waits_and_opens_browser(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            self.create_minimal_repo(repo)
            bin_dir = self.create_fake_bin(repo)
            log_path = repo / "start-prod.log"

            result = subprocess.run(
                ["bash", "scripts/launch.sh"],
                cwd=repo,
                check=True,
                capture_output=True,
                text=True,
                env={
                    "PATH": f"{bin_dir}:{'/usr/bin:/bin'}",
                    "START_PROD_LOG": str(log_path),
                },
            )

            log = log_path.read_text(encoding="utf-8")
            self.assertIn("docker compose up -d --build", log)
            self.assertIn("curl -fsS http://localhost:5174/health", log)
            self.assertIn("open http://localhost:5174", log)
            self.assertIn("ChatBI is ready at http://localhost:5174", result.stdout)

    def test_launch_copies_example_env_when_no_runtime_env_exists(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            self.create_minimal_repo(repo)
            bin_dir = self.create_fake_bin(repo)
            log_path = repo / "start-prod.log"

            result = subprocess.run(
                ["bash", "scripts/launch.sh", "--no-open"],
                cwd=repo,
                check=True,
                capture_output=True,
                text=True,
                env={
                    "PATH": f"{bin_dir}:{'/usr/bin:/bin'}",
                    "START_PROD_LOG": str(log_path),
                },
            )

            self.assertEqual(
                (repo / ".env").read_text(encoding="utf-8"),
                (repo / ".env.example").read_text(encoding="utf-8"),
            )
            self.assertIn("No env file found; copied .env.example to .env", result.stdout)

    def test_launch_keeps_existing_runtime_env(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            self.create_minimal_repo(repo)
            (repo / ".env").write_text(
                "CHATBI_SEED_USERS=ops:ops123:admin;demo:demo123:user\n",
                encoding="utf-8",
            )
            bin_dir = self.create_fake_bin(repo)
            log_path = repo / "start-prod.log"

            result = subprocess.run(
                ["bash", "scripts/launch.sh", "--no-open"],
                cwd=repo,
                check=True,
                capture_output=True,
                text=True,
                env={
                    "PATH": f"{bin_dir}:{'/usr/bin:/bin'}",
                    "START_PROD_LOG": str(log_path),
                },
            )

            self.assertTrue((repo / ".env").exists())
            self.assertNotIn("copied .env.example", result.stdout)

    def test_launch_can_skip_build_and_browser(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            self.create_minimal_repo(repo)
            bin_dir = self.create_fake_bin(repo)
            log_path = repo / "start-prod.log"

            subprocess.run(
                [
                    "bash",
                    "scripts/launch.sh",
                    "--no-build",
                    "--no-open",
                    "--url",
                    "http://127.0.0.1:9999",
                ],
                cwd=repo,
                check=True,
                capture_output=True,
                text=True,
                env={
                    "PATH": f"{bin_dir}:{'/usr/bin:/bin'}",
                    "START_PROD_LOG": str(log_path),
                },
            )

            log = log_path.read_text(encoding="utf-8")
            self.assertIn("docker compose up -d", log)
            self.assertNotIn("--build", log)
            self.assertIn("curl -fsS http://127.0.0.1:9999/health", log)
            self.assertNotIn("open ", log)

    def test_deploy_workflows_use_frontend_default_port(self) -> None:
        for path in (
            ROOT / ".github/workflows/deploy-pre.yml",
            ROOT / ".github/workflows/deploy-prod.yml",
        ):
            workflow = path.read_text(encoding="utf-8")

            self.assertIn("http://localhost:5174", workflow)
            self.assertNotIn("http://localhost:5173", workflow)

    def test_compose_defaults_use_build_mirrors(self) -> None:
        compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

        self.assertIn("m.daocloud.io/docker.io/library/node:22-bookworm-slim", dockerfile)
        self.assertIn("m.daocloud.io/docker.io/library/python:3.11-slim", dockerfile)
        self.assertIn("m.daocloud.io/docker.io/library/mysql:8.0", compose)
        self.assertIn("https://registry.npmmirror.com", dockerfile)
        self.assertNotIn("NODE_IMAGE", compose + dockerfile)
        self.assertNotIn("PYTHON_IMAGE", compose + dockerfile)
        self.assertNotIn("MYSQL_IMAGE", compose)
        self.assertNotIn("NPM_REGISTRY", compose + dockerfile)
