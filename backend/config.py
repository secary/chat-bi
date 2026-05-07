import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:

    def load_dotenv() -> None:
        return None


load_dotenv()


@dataclass(frozen=True)
class Settings:
    llm_model: str = field(
        default_factory=lambda: os.getenv("LLM_MODEL", "gpt-4o-mini")
    )
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    api_base: str = field(default_factory=lambda: os.getenv("API_BASE", ""))

    db_host: str = field(
        default_factory=lambda: os.getenv("CHATBI_DB_HOST", "127.0.0.1")
    )
    db_port: str = field(default_factory=lambda: os.getenv("CHATBI_DB_PORT", "3307"))
    db_user: str = field(
        default_factory=lambda: os.getenv("CHATBI_DB_USER", "demo_user")
    )
    db_password: str = field(
        default_factory=lambda: os.getenv("CHATBI_DB_PASSWORD", "demo_pass")
    )
    db_name: str = field(
        default_factory=lambda: os.getenv("CHATBI_DB_NAME", "chatbi_demo")
    )
    app_db_host: str = field(
        default_factory=lambda: os.getenv(
            "CHATBI_APP_DB_HOST", os.getenv("CHATBI_DB_HOST", "127.0.0.1")
        )
    )
    app_db_port: str = field(
        default_factory=lambda: os.getenv(
            "CHATBI_APP_DB_PORT", os.getenv("CHATBI_DB_PORT", "3307")
        )
    )
    app_db_user: str = field(
        default_factory=lambda: os.getenv(
            "CHATBI_APP_DB_USER", os.getenv("CHATBI_DB_USER", "demo_user")
        )
    )
    app_db_password: str = field(
        default_factory=lambda: os.getenv(
            "CHATBI_APP_DB_PASSWORD", os.getenv("CHATBI_DB_PASSWORD", "demo_pass")
        )
    )
    app_db_name: str = field(
        default_factory=lambda: os.getenv("CHATBI_APP_DB_NAME", "chatbi_app")
    )
    admin_db_host: str = field(
        default_factory=lambda: os.getenv(
            "CHATBI_ADMIN_DB_HOST",
            os.getenv("CHATBI_APP_DB_HOST", os.getenv("CHATBI_DB_HOST", "127.0.0.1")),
        )
    )
    admin_db_port: str = field(
        default_factory=lambda: os.getenv(
            "CHATBI_ADMIN_DB_PORT",
            os.getenv("CHATBI_APP_DB_PORT", os.getenv("CHATBI_DB_PORT", "3307")),
        )
    )
    admin_db_user: str = field(
        default_factory=lambda: os.getenv(
            "CHATBI_ADMIN_DB_USER",
            os.getenv("CHATBI_APP_DB_USER", os.getenv("CHATBI_DB_USER", "demo_user")),
        )
    )
    admin_db_password: str = field(
        default_factory=lambda: os.getenv(
            "CHATBI_ADMIN_DB_PASSWORD",
            os.getenv(
                "CHATBI_APP_DB_PASSWORD", os.getenv("CHATBI_DB_PASSWORD", "demo_pass")
            ),
        )
    )
    admin_db_name: str = field(
        default_factory=lambda: os.getenv("CHATBI_ADMIN_DB_NAME", "chatbi_admin")
    )
    log_db_host: str = field(
        default_factory=lambda: os.getenv(
            "CHATBI_LOG_DB_HOST", os.getenv("CHATBI_DB_HOST", "127.0.0.1")
        )
    )
    log_db_port: str = field(
        default_factory=lambda: os.getenv(
            "CHATBI_LOG_DB_PORT", os.getenv("CHATBI_DB_PORT", "3307")
        )
    )
    log_db_user: str = field(
        default_factory=lambda: os.getenv(
            "CHATBI_LOG_DB_USER", os.getenv("CHATBI_DB_USER", "demo_user")
        )
    )
    log_db_password: str = field(
        default_factory=lambda: os.getenv(
            "CHATBI_LOG_DB_PASSWORD", os.getenv("CHATBI_DB_PASSWORD", "demo_pass")
        )
    )
    log_db_name: str = field(
        default_factory=lambda: os.getenv("CHATBI_LOG_DB_NAME", "chatbi_logs")
    )

    agent_react: bool = field(
        default_factory=lambda: os.getenv("CHATBI_AGENT_REACT", "1").strip().lower()
        not in ("0", "false", "no", "off")
    )
    agent_max_steps: int = field(
        default_factory=lambda: max(1, int(os.getenv("CHATBI_AGENT_MAX_STEPS", "8")))
    )

    jwt_secret: str = field(
        default_factory=lambda: os.getenv("CHATBI_JWT_SECRET", "chatbi-dev-change-me")
    )
    jwt_exp_hours: int = field(
        default_factory=lambda: max(1, int(os.getenv("CHATBI_JWT_EXP_HOURS", "168")))
    )

    project_root: Path = Path(__file__).resolve().parent.parent
    skills_dir: Path = field(init=False)

    def __post_init__(self):
        object.__setattr__(self, "skills_dir", self.project_root / "skills")

    @property
    def db_config(self) -> dict[str, str]:
        return {
            "host": self.db_host,
            "port": self.db_port,
            "user": self.db_user,
            "password": self.db_password,
            "database": self.db_name,
        }

    @property
    def log_db_config(self) -> dict[str, str]:
        return {
            "host": self.log_db_host,
            "port": self.log_db_port,
            "user": self.log_db_user,
            "password": self.log_db_password,
            "database": self.log_db_name,
        }

    @property
    def app_db_config(self) -> dict[str, str]:
        return {
            "host": self.app_db_host,
            "port": self.app_db_port,
            "user": self.app_db_user,
            "password": self.app_db_password,
            "database": self.app_db_name,
        }

    @property
    def admin_db_config(self) -> dict[str, str]:
        return {
            "host": self.admin_db_host,
            "port": self.admin_db_port,
            "user": self.admin_db_user,
            "password": self.admin_db_password,
            "database": self.admin_db_name,
        }

    @property
    def llm_params(self) -> dict:
        params: dict[str, object] = {"model": self.llm_model}
        if self.openai_api_key:
            params["api_key"] = self.openai_api_key
        if self.api_base:
            params["api_base"] = self.api_base
        return params


settings = Settings()
