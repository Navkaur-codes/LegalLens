"""PDF validation and page-by-page text extraction (in memory only)."""

import re
from dataclasses import dataclass

import pymupdf

from app.config import Settings
from app.errors import PdfValidationError

ALLOWED_CONTENT_TYPES = {"application/pdf", "application/x-pdf", "application/octet-stream"}

# Default text flags minus TEXT_PRESERVE_LIGATURES, so "ﬁ" is extracted as "fi".
_TEXT_FLAGS = pymupdf.TEXT_PRESERVE_WHITESPACE | pymupdf.TEXT_MEDIABOX_CLIP

_INLINE_SPACE = re.compile(r"[ \t ]+")


@dataclass(frozen=True)
class ExtractedDocument:
    """Extracted text; pages[0] is page 1."""

    pages: list[str]

    @property
    def page_count(self) -> int:
        return len(self.pages)

    @property
    def char_count(self) -> int:
        return sum(len(page) for page in self.pages)


def clean_page_text(text: str) -> str:
    """Collapse inline whitespace and drop empty lines, keeping line structure."""
    lines = (_INLINE_SPACE.sub(" ", line).strip() for line in text.splitlines())
    return "\n".join(line for line in lines if line)


def extract_pdf(data: bytes, content_type: str | None, settings: Settings) -> ExtractedDocument:
    """Validate an uploaded PDF against the configured limits and return its text by page.

    Raises PdfValidationError with a user-friendly message and the matching HTTP status.
    """
    if len(data) > settings.max_file_bytes:
        raise PdfValidationError(f"The file is larger than {settings.max_file_mb} MB.", 413)
    if (content_type and content_type not in ALLOWED_CONTENT_TYPES) or not data.startswith(b"%PDF"):
        raise PdfValidationError("Please upload a PDF file.")

    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise PdfValidationError("This PDF could not be read. It may be damaged.") from exc

    with doc:
        if doc.needs_pass or doc.is_encrypted:
            raise PdfValidationError("This PDF is password-protected. Please upload an unlocked copy.")
        if doc.page_count > settings.max_pages:
            raise PdfValidationError(
                f"This PDF has {doc.page_count} pages. The limit is {settings.max_pages} pages.", 413
            )
        pages = [clean_page_text(page.get_text("text", flags=_TEXT_FLAGS)) for page in doc]

    document = ExtractedDocument(pages=pages)
    if document.char_count < settings.min_chars:
        raise PdfValidationError(
            "No readable text was found. Scanned or image-only PDFs are not supported; please upload a text-based PDF.",
            422,
        )
    if document.char_count > settings.max_chars:
        raise PdfValidationError(
            f"This document has {document.char_count:,} characters of text. "
            f"The limit is {settings.max_chars:,} characters.",
            413,
        )
    return document
