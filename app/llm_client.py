"""Brief generators: a mock (default, zero API calls) and a live Groq client."""

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Protocol

import groq
from fastapi import Depends
from pydantic import ValidationError

from app.config import MOCK_LLM_OUTPUT_PATH, Settings, get_settings
from app.errors import LLMServiceError
from app.prompts import build_messages, build_repair_message
from app.schemas import LLMBrief

logger = logging.getLogger(__name__)

BUSY_MESSAGE = "The AI service is busy right now. Please try again shortly."
UNAVAILABLE_MESSAGE = "The AI service is unavailable right now. Please try again later."
BAD_RESPONSE_MESSAGE = "The AI response could not be processed. Please try again."


class BriefGenerator(Protocol):
    is_mock: bool

    def generate(self, pages: list[str]) -> LLMBrief: ...


def parse_brief(raw: str) -> LLMBrief:
    """Parse and validate model output. Raises ValidationError for bad JSON or wrong shape."""
    return LLMBrief.model_validate_json(raw)


@lru_cache(maxsize=4)
def load_fixture(path: Path) -> LLMBrief:
    """Parse the mock fixture once; the pipeline never mutates it."""
    return parse_brief(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=4)
def shared_groq_client(api_key: str, timeout_s: float) -> groq.Groq:
    """One client per key, so HTTP connections are pooled and reused across requests."""
    return groq.Groq(api_key=api_key, timeout=timeout_s, max_retries=0)


class MockBriefGenerator:
    """Returns a fixed, hand-written brief for the fictional sample. Makes no network calls."""

    is_mock = True

    def __init__(self, fixture_path: Path = MOCK_LLM_OUTPUT_PATH) -> None:
        self._fixture_path = fixture_path

    def generate(self, pages: list[str]) -> LLMBrief:
        return load_fixture(self._fixture_path)


class GroqBriefGenerator:
    """One Groq chat completion per brief, with at most one repair retry on invalid output."""

    is_mock = False

    def __init__(self, settings: Settings, client: Any | None = None) -> None:
        self._settings = settings
        self._client = client or shared_groq_client(settings.groq_api_key, settings.groq_timeout_s)

    def generate(self, pages: list[str]) -> LLMBrief:
        messages = build_messages(pages)
        raw = self._complete(messages)
        try:
            return parse_brief(raw)
        except ValidationError as first_error:
            logger.warning("LLM output failed validation; attempting one repair")
            messages += [{"role": "assistant", "content": raw}, build_repair_message(str(first_error))]

        raw = self._complete(messages)
        try:
            return parse_brief(raw)
        except ValidationError as exc:
            logger.warning("LLM output failed validation after repair")
            raise LLMServiceError(BAD_RESPONSE_MESSAGE) from exc

    def _complete(self, messages: list[dict[str, str]]) -> str:
        options: dict[str, Any] = {}
        if self._settings.groq_reasoning_effort:
            options["reasoning_effort"] = self._settings.groq_reasoning_effort
        try:
            response = self._client.chat.completions.create(
                model=self._settings.groq_model,
                messages=messages,
                temperature=self._settings.groq_temperature,
                max_tokens=self._settings.groq_max_tokens,
                response_format={"type": "json_object"},
                **options,
            )
        except (groq.RateLimitError, groq.APITimeoutError) as exc:
            logger.warning("Groq busy: %s", type(exc).__name__)
            raise LLMServiceError(BUSY_MESSAGE) from exc
        except groq.NotFoundError as exc:
            logger.error("Groq model not found: %s (check GROQ_MODEL)", self._settings.groq_model)
            raise LLMServiceError(UNAVAILABLE_MESSAGE) from exc
        except groq.APIError as exc:
            logger.error("Groq API error: %s", type(exc).__name__)
            raise LLMServiceError(UNAVAILABLE_MESSAGE) from exc
        return response.choices[0].message.content or ""


def get_brief_generator(settings: Settings = Depends(get_settings)) -> BriefGenerator:
    """Pick the generator from LLM_MODE. Never falls back silently from groq to mock."""
    if settings.llm_mode == "groq":
        if not settings.groq_api_key:
            raise LLMServiceError("Live AI mode is enabled but no API key is configured.", 503)
        return GroqBriefGenerator(settings)
    return MockBriefGenerator()
