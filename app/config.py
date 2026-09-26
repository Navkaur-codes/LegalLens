"""Application settings. All limits are defined here once and exposed via GET /api/config."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
SAMPLES_DIR = BASE_DIR / "samples"
SAMPLE_PDF_PATH = SAMPLES_DIR / "sample_agreement.pdf"
SAMPLE_BRIEF_PATH = SAMPLES_DIR / "sample_brief.json"
MOCK_LLM_OUTPUT_PATH = SAMPLES_DIR / "mock_llm_output.json"


class Settings(BaseSettings):
    """Runtime configuration, read from environment variables or a local .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM: mock is the default so development and tests never spend Groq quota.
    llm_mode: Literal["mock", "groq"] = "mock"
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    # For reasoning models (gpt-oss): low effort leaves most of the token budget for the JSON brief.
    # Set to an empty value for models that do not accept this parameter.
    groq_reasoning_effort: str | None = "low"
    groq_max_tokens: int = 3000
    groq_temperature: float = 0.2
    groq_timeout_s: float = 45.0

    # Document limits.
    max_file_mb: int = 5
    max_pages: int = 10
    max_chars: int = 18_000
    min_chars: int = 200

    # Per-IP rate limit for POST /api/brief.
    rate_limit_requests: int = 5
    rate_limit_window_s: int = 600

    @property
    def max_file_bytes(self) -> int:
        return self.max_file_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
