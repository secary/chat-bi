from __future__ import annotations

from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:

    def load_dotenv(*_args, **_kwargs) -> None:
        return None


def load_project_env(project_root: Path) -> None:
    """Load base env first, then dev env as an override for local testing."""
    load_dotenv(project_root / ".env")
    load_dotenv(project_root / ".env.dev", override=True)
    load_dotenv(project_root / "env.dev", override=True)
