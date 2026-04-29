from __future__ import annotations

import csv
import os
import subprocess
from typing import Dict, List, Optional


def default_db() -> Dict[str, str]:
    return {
        "host": os.getenv("CHATBI_DB_HOST", "127.0.0.1"),
        "port": os.getenv("CHATBI_DB_PORT", "3307"),
        "user": os.getenv("CHATBI_DB_USER", "demo_user"),
        "password": os.getenv("CHATBI_DB_PASSWORD", "demo_pass"),
        "database": os.getenv("CHATBI_DB_NAME", "chatbi_demo"),
    }


class MysqlCli:
    def __init__(self, config: Dict[str, str]):
        self.config = config
        self.mysql_cmd = os.getenv("CHATBI_MYSQL_CMD", "mysql")

    def query(self, sql: str) -> List[Dict[str, str]]:
        base_cmd = [
            self.mysql_cmd,
            f"-h{self.config['host']}",
            f"-P{self.config['port']}",
            f"-u{self.config['user']}",
            f"-p{self.config['password']}",
        ]
        tail_cmd = [
            "--batch",
            "--raw",
            "--default-character-set=utf8mb4",
            self.config["database"],
            "-e",
            sql,
        ]
        proc = self._run_with_ssl_fallback(base_cmd, tail_cmd)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or proc.stdout.strip())
        lines = [line for line in proc.stdout.splitlines() if line.strip()]
        if not lines:
            return []
        return [dict(row) for row in csv.DictReader(lines, delimiter="\t")]

    def _run_with_ssl_fallback(
        self, base_cmd: List[str], tail_cmd: List[str]
    ) -> subprocess.CompletedProcess[str]:
        attempts = [["--ssl-mode=DISABLED"], ["--ssl=0"], []]
        last_proc: Optional[subprocess.CompletedProcess[str]] = None
        for ssl_args in attempts:
            proc = subprocess.run(
                [*base_cmd, *ssl_args, *tail_cmd],
                text=True,
                capture_output=True,
                check=False,
            )
            last_proc = proc
            error = proc.stderr.strip()
            if proc.returncode == 0:
                return proc
            if "unknown variable" in error and ("ssl-mode" in error or "ssl=0" in error):
                continue
            if "TLS/SSL error" in error or "self-signed certificate" in error:
                continue
            return proc
        if last_proc is None:
            raise RuntimeError("mysql command was not executed")
        return last_proc


def quote_ident(identifier: str) -> str:
    if not identifier or "`" in identifier or "\x00" in identifier:
        raise ValueError(f"Unsafe identifier: {identifier}")
    return f"`{identifier}`"


def quote_literal(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "''") + "'"
