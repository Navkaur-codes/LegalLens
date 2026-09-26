import pytest

from app.errors import PdfValidationError
from app.pdf_extractor import extract_pdf

LONG_TEXT = "The Employee shall give sixty days written notice before resigning. " * 5


def _error(data: bytes, settings, content_type: str | None = "application/pdf") -> PdfValidationError:
    with pytest.raises(PdfValidationError) as info:
        extract_pdf(data, content_type, settings)
    return info.value


def test_extracts_text_page_by_page(make_pdf, settings):
    document = extract_pdf(make_pdf([LONG_TEXT, "Second page. " + LONG_TEXT]), "application/pdf", settings)

    assert document.page_count == 2
    assert document.pages[1].startswith("Second page.")
    assert document.char_count == sum(len(page) for page in document.pages)


def test_sample_agreement_is_valid_and_labelled_fictional(sample_pdf, settings):
    document = extract_pdf(sample_pdf, "application/pdf", settings)

    assert document.char_count <= settings.max_chars
    assert all("FICTIONAL DEMONSTRATION DOCUMENT" in page for page in document.pages)
    assert "ﬁ" not in "".join(document.pages)  # ligatures are expanded for reliable quote matching


def test_rejects_non_pdf_bytes(settings):
    error = _error(b"just some text", settings)
    assert error.status_code == 400


def test_rejects_wrong_content_type(make_pdf, settings):
    error = _error(make_pdf([LONG_TEXT]), settings, content_type="text/plain")
    assert error.status_code == 400


def test_rejects_damaged_pdf(settings):
    error = _error(b"%PDF-1.7 this is not really a pdf", settings)
    assert error.status_code == 400


def test_rejects_encrypted_pdf(make_pdf, settings):
    error = _error(make_pdf([LONG_TEXT], encrypt=True), settings)
    assert error.status_code == 400
    assert "password" in error.message


def test_rejects_file_over_size_limit(settings):
    small = settings.model_copy(update={"max_file_mb": 1})
    error = _error(b"%PDF" + b"0" * (1024 * 1024), small)
    assert error.status_code == 413


def test_rejects_too_many_pages(make_pdf, settings):
    limited = settings.model_copy(update={"max_pages": 2})
    error = _error(make_pdf([LONG_TEXT] * 3), limited)
    assert error.status_code == 413
    assert "2 pages" in error.message


def test_rejects_scanned_or_empty_pdf(make_pdf, settings):
    error = _error(make_pdf(["", ""]), settings)
    assert error.status_code == 422


def test_rejects_too_many_characters(make_pdf, settings):
    limited = settings.model_copy(update={"max_chars": 250})
    error = _error(make_pdf([LONG_TEXT]), limited)
    assert error.status_code == 413
    assert "250" in error.message
