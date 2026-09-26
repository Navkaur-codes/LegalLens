"""Server-side source verification: is the cited quote really in the document?

Verification proves the quote is present. It does not prove the explanation is correct.
"""

import re
import unicodedata
from typing import Any

from app.schemas import CitedSource, LLMBrief, VerifiedBrief, VerifiedSource

_PUNCTUATION = str.maketrans(
    {
        "\N{LEFT SINGLE QUOTATION MARK}": "'",
        "\N{RIGHT SINGLE QUOTATION MARK}": "'",
        "\N{SINGLE LOW-9 QUOTATION MARK}": "'",
        "\N{PRIME}": "'",
        "\N{LEFT DOUBLE QUOTATION MARK}": '"',
        "\N{RIGHT DOUBLE QUOTATION MARK}": '"',
        "\N{DOUBLE LOW-9 QUOTATION MARK}": '"',
        "\N{DOUBLE PRIME}": '"',
        "\N{HYPHEN}": "-",
        "\N{NON-BREAKING HYPHEN}": "-",
        "\N{FIGURE DASH}": "-",
        "\N{EN DASH}": "-",
        "\N{EM DASH}": "-",
        "\N{MINUS SIGN}": "-",
    }
)
_WHITESPACE = re.compile(r"\s+")
_EDGE_CHARS = " \"'.,;:-\N{HORIZONTAL ELLIPSIS}"


def normalize(text: str) -> str:
    """Normalise for matching: ligatures (NFKC), quotes, dashes, whitespace and case."""
    text = unicodedata.normalize("NFKC", text).translate(_PUNCTUATION)
    return _WHITESPACE.sub(" ", text).strip().lower()


def normalize_pages(pages: list[str]) -> list[str]:
    return [normalize(page) for page in pages]


def verify_source(source: CitedSource, normalized_pages: list[str]) -> VerifiedSource:
    """Check the quote on the cited page first, then on every page (correcting the page number)."""
    needle = normalize(source.quote or "").strip(_EDGE_CHARS)
    if not needle:
        return VerifiedSource(**source.model_dump(), verified=False)

    cited_index = (source.page or 0) - 1
    if 0 <= cited_index < len(normalized_pages) and needle in normalized_pages[cited_index]:
        return VerifiedSource(**source.model_dump(), verified=True)

    for index, page_text in enumerate(normalized_pages):
        if needle in page_text:
            return VerifiedSource(**source.model_dump(exclude={"page"}), page=index + 1, verified=True)

    return VerifiedSource(**source.model_dump(), verified=False)


def ground_brief(brief: LLMBrief, pages: list[str]) -> VerifiedBrief:
    """Return the brief with every `source` (wherever it appears) verified against the document pages."""
    normalized_pages = normalize_pages(pages)

    def ground(node: Any) -> Any:
        if isinstance(node, list):
            return [ground(item) for item in node]
        if isinstance(node, dict):
            return {
                key: verify_source(CitedSource.model_validate(value), normalized_pages).model_dump()
                if key == "source"
                else ground(value)
                for key, value in node.items()
            }
        return node

    return VerifiedBrief.model_validate(ground(brief.model_dump()))
