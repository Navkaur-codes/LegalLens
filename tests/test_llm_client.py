"""Groq generator behaviour, using a fake client (no network)."""

import json
from types import SimpleNamespace

import groq
import httpx
import pytest

from app.errors import LLMServiceError
from app.llm_client import (
    BAD_RESPONSE_MESSAGE,
    BUSY_MESSAGE,
    UNAVAILABLE_MESSAGE,
    GroqBriefGenerator,
    MockBriefGenerator,
    get_brief_generator,
    shared_groq_client,
)
from app.schemas import MAX_NEXT_STEPS, LLMBrief

VALID_JSON = json.dumps(
    {
        "is_employment_document": True,
        "overview": {"summary": "An employment agreement.", "key_terms": []},
        "responsibilities": [
            {
                "title": "Give notice",
                "description": "60 days notice.",
                "category": "surprise-category",
                "source": {"page": 1, "quote": "60 days"},
            }
        ],
        "clauses_to_review": [
            {
                "title": "Bond",
                "topic": "bond",
                "what_it_says": "24 months.",
                "why_it_matters": "Cost of leaving.",
                "questions_to_ask": ["One?", "Two?", "Three?", "Four?"],
                "source": {"page": 1},
            }
        ],
    }
)


class FakeClient:
    """Mimics groq.Groq().chat.completions.create with scripted replies."""

    def __init__(self, replies: list) -> None:
        self.replies = list(replies)
        self.calls: list[dict] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=reply))])


def _generator(settings, replies: list) -> tuple[GroqBriefGenerator, FakeClient]:
    fake = FakeClient(replies)
    return GroqBriefGenerator(settings, client=fake), fake


def test_valid_output_uses_one_call_with_json_mode(settings):
    generator, fake = _generator(settings, [VALID_JSON])
    brief = generator.generate(["page text"])

    assert isinstance(brief, LLMBrief)
    assert len(fake.calls) == 1
    assert fake.calls[0]["response_format"] == {"type": "json_object"}
    assert fake.calls[0]["model"] == settings.groq_model
    assert fake.calls[0]["reasoning_effort"] == "low"
    assert '<page n="1">' in fake.calls[0]["messages"][1]["content"]


def test_reasoning_effort_is_omitted_when_not_configured(settings):
    plain = settings.model_copy(update={"groq_reasoning_effort": None})
    generator, fake = _generator(plain, [VALID_JSON])
    generator.generate(["page text"])

    assert "reasoning_effort" not in fake.calls[0]


def test_unknown_model_returns_unavailable_message(settings):
    response = httpx.Response(404, request=httpx.Request("POST", "https://api.groq.com"))
    generator, _ = _generator(settings, [groq.NotFoundError("model not found", response=response, body=None)])

    with pytest.raises(LLMServiceError) as info:
        generator.generate(["page text"])
    assert info.value.message == UNAVAILABLE_MESSAGE


def test_output_is_normalised_to_schema(settings):
    generator, _ = _generator(settings, [VALID_JSON])
    brief = generator.generate(["page text"])

    assert brief.responsibilities[0].category == "other"
    assert len(brief.clauses_to_review[0].questions_to_ask) == 3


def test_invalid_output_is_repaired_once(settings):
    generator, fake = _generator(settings, ["not json", VALID_JSON])
    generator.generate(["page text"])

    assert len(fake.calls) == 2
    assert "not valid JSON" in fake.calls[1]["messages"][-1]["content"]


def test_invalid_output_twice_raises_502(settings):
    generator, fake = _generator(settings, ["not json", '{"still": "wrong"}'])
    with pytest.raises(LLMServiceError) as info:
        generator.generate(["page text"])

    assert len(fake.calls) == 2
    assert info.value.status_code == 502 and info.value.message == BAD_RESPONSE_MESSAGE


def test_provider_rate_limit_shows_busy_message(settings):
    response = httpx.Response(429, request=httpx.Request("POST", "https://api.groq.com"))
    generator, _ = _generator(settings, [groq.RateLimitError("rate limited", response=response, body=None)])

    with pytest.raises(LLMServiceError) as info:
        generator.generate(["page text"])
    assert info.value.message == BUSY_MESSAGE


def test_groq_client_is_shared_between_requests():
    first = shared_groq_client("test-key", 30.0)  # constructing a client makes no network call
    assert shared_groq_client("test-key", 30.0) is first
    assert shared_groq_client("other-key", 30.0) is not first


def test_mock_generator_returns_the_fixture_without_network():
    generator = MockBriefGenerator()
    assert generator.is_mock is True
    assert generator.generate(["any page"]).action_plan.next_steps


def test_next_steps_are_capped_and_blank_items_dropped():
    data = json.loads(VALID_JSON)
    data["action_plan"] = {"next_steps": ["  "] + [f"Step {n}" for n in range(10)]}
    brief = LLMBrief.model_validate(data)

    assert len(brief.action_plan.next_steps) == MAX_NEXT_STEPS
    assert brief.action_plan.next_steps[0] == "Step 0"


def test_action_plan_defaults_to_empty_when_model_omits_it(settings):
    generator, _ = _generator(settings, [VALID_JSON])
    plan = generator.generate(["page text"]).action_plan

    assert plan.missing_or_unclear == [] and plan.next_steps == []


def test_other_provider_errors_show_unavailable_message(settings):
    response = httpx.Response(500, request=httpx.Request("POST", "https://api.groq.com"))
    generator, _ = _generator(settings, [groq.InternalServerError("boom", response=response, body=None)])

    with pytest.raises(LLMServiceError) as info:
        generator.generate(["page text"])
    assert info.value.message == UNAVAILABLE_MESSAGE


def test_live_mode_with_key_selects_groq_generator(settings):
    live = settings.model_copy(update={"llm_mode": "groq", "groq_api_key": "test-key"})
    generator = get_brief_generator(live)  # builds a client object only; no request is sent

    assert isinstance(generator, GroqBriefGenerator) and generator.is_mock is False


def test_mock_mode_selects_mock_generator(settings):
    assert isinstance(get_brief_generator(settings), MockBriefGenerator)
