import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    llm_model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "gpt-4o-mini"))
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    api_base: str = field(default_factory=lambda: os.getenv("API_BASE", ""))

    db_host: str = field(default_factory=lambda: os.getenv("CHATBI_DB_HOST", "127.0.0.1"))
    db_port: str = field(default_factory=lambda: os.getenv("CHATBI_DB_PORT", "3307"))
    db_user: str = field(default_factory=lambda: os.getenv("CHATBI_DB_USER", "demo_user"))
    db_password: str = field(default_factory=lambda: os.getenv("CHATBI_DB_PASSWORD", "demo_pass"))
    db_name: str = field(default_factory=lambda: os.getenv("CHATBI_DB_NAME", "chatbi_demo"))

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
    def llm_params(self) -> dict:
        params: dict[str, object] = {"model": self.llm_model}
        if self.api_base:
            params["api_base"] = self.api_base
        return params


settings = Settings()
