from __future__ import annotations

from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:

    def load_dotenv(*_args, **_kwargs) -> None:
        return None


def load_project_env(project_root: Path) -> None:
    """Load only the production-style base env.

    Local development loads .env.dev explicitly from scripts/start_dev.sh so
    production/manual backend runs cannot be shadowed by dev-only settings.
    """
    load_dotenv(project_root / ".env")
