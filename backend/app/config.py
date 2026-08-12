import os
from dataclasses import dataclass
from typing import Literal, cast


@dataclass(frozen=True)
class Settings:
    provider_mode: Literal["mock", "openai"] = "mock"
    openai_api_key: str | None = None
    analyzer_model: str = "gpt-5.6-luna"
    tutor_model: str = "gpt-5.6-terra"
    reasoning_effort: str = "medium"
    openai_timeout_seconds: float = 30.0
    token_ttl_seconds: int = 86_400

    @classmethod
    def from_env(cls) -> "Settings":
        mode = os.getenv("APP_PROVIDER_MODE", "mock").strip().lower()
        if mode not in {"mock", "openai"}:
            raise ValueError("APP_PROVIDER_MODE must be mock or openai")
        api_key = os.getenv("OPENAI_API_KEY") or None
        if mode == "openai" and api_key is None:
            raise ValueError("OPENAI_API_KEY is required in openai mode")
        return cls(
            provider_mode=cast(Literal["mock", "openai"], mode),
            openai_api_key=api_key,
            analyzer_model=os.getenv("OPENAI_ANALYZER_MODEL", "gpt-5.6-luna"),
            tutor_model=os.getenv("OPENAI_TUTOR_MODEL", "gpt-5.6-terra"),
            reasoning_effort=os.getenv("OPENAI_REASONING_EFFORT", "medium"),
            openai_timeout_seconds=float(os.getenv("OPENAI_TIMEOUT_SECONDS", "30")),
            token_ttl_seconds=int(os.getenv("AUTH_TOKEN_TTL_SECONDS", "86400")),
        )
