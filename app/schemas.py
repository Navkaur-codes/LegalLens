"""Pydantic models for the LLM output and the API response.

Findings are generic over their source type: the LLM returns `CitedSource` (no `verified`
field, so the model can never claim verification), and the server upgrades each one to a
`VerifiedSource` after checking the quote against the document.
"""

from typing import Any, Generic, Literal, TypeVar, get_args

from pydantic import BaseModel, Field, field_validator

DISCLAIMER = (
    "LegalLens provides general legal information to help you understand your document. "
    "It is not legal advice and does not assess whether any clause is valid or enforceable. "
    "For decisions, consult a qualified lawyer or your HR team."
)
VERIFICATION_NOTE = (
    "Source verification checks that the quoted text appears in your document. "
    "It does not confirm that the explanation is legally accurate."
)

ResponsibilityCategory = Literal["obligation", "deadline", "notice", "date", "other"]
ClauseTopic = Literal[
    "bond", "non_compete", "termination", "confidentiality", "ip", "compensation", "working_terms", "other"
]
MAX_QUESTIONS = 3
MAX_NEXT_STEPS = 6


def _non_blank(items: list[str], limit: int) -> list[str]:
    return [item for item in items if item.strip()][:limit]


def _choice_or_other(value: Any, allowed: tuple[str, ...]) -> Any:
    """Map unexpected enum values from the model to "other" instead of failing validation."""
    return value if value in allowed else "other"


class CitedSource(BaseModel):
    """Where a finding comes from, as cited by the model."""

    page: int | None = Field(default=None, ge=1)
    section: str | None = None
    quote: str | None = None


class VerifiedSource(CitedSource):
    """A cited source after server-side quote verification."""

    verified: bool = False


SourceT = TypeVar("SourceT", bound=CitedSource)


class KeyTerm(BaseModel, Generic[SourceT]):
    term: str
    value: str | None = None
    explanation: str
    source: SourceT


class Responsibility(BaseModel, Generic[SourceT]):
    title: str
    description: str
    category: ResponsibilityCategory = "other"
    timing: str | None = None
    source: SourceT

    @field_validator("category", mode="before")
    @classmethod
    def _category(cls, value: Any) -> Any:
        return _choice_or_other(value, get_args(ResponsibilityCategory))


class ClauseToReview(BaseModel, Generic[SourceT]):
    title: str
    topic: ClauseTopic = "other"
    what_it_says: str
    why_it_matters: str
    questions_to_ask: list[str] = Field(default_factory=list)
    source: SourceT

    @field_validator("topic", mode="before")
    @classmethod
    def _topic(cls, value: Any) -> Any:
        return _choice_or_other(value, get_args(ClauseTopic))

    @field_validator("questions_to_ask")
    @classmethod
    def _limit_questions(cls, value: list[str]) -> list[str]:
        return _non_blank(value, MAX_QUESTIONS)


class MissingOrUnclear(BaseModel, Generic[SourceT]):
    """Information the document references but does not include, leaves blank, or states inconsistently."""

    title: str
    detail: str
    source: SourceT


class ActionPlan(BaseModel, Generic[SourceT]):
    missing_or_unclear: list[MissingOrUnclear[SourceT]] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)

    @field_validator("next_steps")
    @classmethod
    def _limit_next_steps(cls, value: list[str]) -> list[str]:
        return _non_blank(value, MAX_NEXT_STEPS)


class Overview(BaseModel, Generic[SourceT]):
    summary: str
    document_type: str | None = None
    employer: str | None = None
    employee: str | None = None
    key_terms: list[KeyTerm[SourceT]] = Field(default_factory=list)


class BriefContent(BaseModel, Generic[SourceT]):
    is_employment_document: bool
    overview: Overview[SourceT]
    responsibilities: list[Responsibility[SourceT]] = Field(default_factory=list)
    clauses_to_review: list[ClauseToReview[SourceT]] = Field(default_factory=list)
    action_plan: ActionPlan[SourceT] = Field(default_factory=dict, validate_default=True)

    def findings(self) -> list[KeyTerm | Responsibility | ClauseToReview | MissingOrUnclear]:
        """Every item that carries a source, in display order."""
        return [
            *self.overview.key_terms,
            *self.responsibilities,
            *self.clauses_to_review,
            *self.action_plan.missing_or_unclear,
        ]


LLMBrief = BriefContent[CitedSource]
"""Exactly what the model must return."""

VerifiedBrief = BriefContent[VerifiedSource]


class DocumentMeta(BaseModel):
    filename: str
    pages: int
    characters: int


class BriefResponse(VerifiedBrief):
    """The API response for POST /api/brief and /api/brief/sample."""

    document: DocumentMeta
    is_demo: bool = False
    is_mock: bool = False  # True when produced by the mock generator, not a live AI analysis
    verification_note: str = VERIFICATION_NOTE
    disclaimer: str = DISCLAIMER


class ClientConfig(BaseModel):
    """Limits and mode the frontend needs, so UI copy always matches the server."""

    max_file_mb: int
    max_pages: int
    max_chars: int
    llm_mode: str
