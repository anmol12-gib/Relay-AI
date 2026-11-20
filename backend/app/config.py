"""Environment configuration. Secrets are never returned to clients."""
from dataclasses import dataclass
import os


def flag(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"true", "1", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    llm_api_keys: tuple[str, ...]
    database_url: str
    allowed_origins: tuple[str, ...]
    enable_failure_simulation: bool
    model: str
    default_system_prompt: str
    request_timeout: int

    @classmethod
    def from_env(cls) -> "Settings":
        keys = tuple(x.strip() for x in os.getenv("LLM_API_KEYS", "").split(",") if x.strip())
        origins = tuple(x.strip().rstrip("/") for x in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",") if x.strip())
        return cls(
            llm_api_keys=keys,
            database_url=os.getenv("DATABASE_URL", "sqlite:////data/app.db"),
            allowed_origins=origins,
            enable_failure_simulation=flag("ENABLE_FAILURE_SIMULATION"),
            model=os.getenv("LLM_MODEL", "gemini/gemini-2.5-flash"),
            default_system_prompt=os.getenv("DEFAULT_SYSTEM_PROMPT", "You are Relay, a thoughtful, precise and helpful AI assistant. Give clear, accurate answers and acknowledge uncertainty."),
            request_timeout=int(os.getenv("LLM_TIMEOUT_SECONDS", "45")),
        )
