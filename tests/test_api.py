import pytest
from fastapi.testclient import TestClient

from app import api
from app.config import get_settings
from app.llm_client import get_brief_generator
from app.main import create_app
from app.middleware import SECURITY_HEADERS
from app.schemas import BriefResponse, LLMBrief


class ExplodingGenerator:
    """Fails the test if the AI generator is ever called."""

    is_mock = False

    def generate(self, pages: list[str]) -> LLMBrief:
        raise AssertionError("generator must not be called")


class NotEmploymentGenerator:
    is_mock = False

    def generate(self, pages: list[str]) -> LLMBrief:
        return LLMBrief.model_validate({"is_employment_document": False, "overview": {"summary": "A restaurant menu."}})


def _all_sources(brief: dict) -> list[dict]:
    return [finding.source.model_dump() for finding in BriefResponse.model_validate(brief).findings()]


def _upload(client, data: bytes, filename: str = "offer.pdf", content_type: str = "application/pdf"):
    return client.post("/api/brief", files={"file": (filename, data, content_type)})


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_config_matches_settings(client, settings):
    assert client.get("/api/config").json() == {
        "max_file_mb": settings.max_file_mb,
        "max_pages": settings.max_pages,
        "max_chars": settings.max_chars,
        "llm_mode": "mock",
    }


def test_frontend_is_served_with_security_headers(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "LegalLens" in response.text
    for header, value in SECURITY_HEADERS.items():
        assert response.headers[header] == value


def test_static_responses_are_compressed(client):
    response = client.get("/", headers={"Accept-Encoding": "gzip"})
    assert response.headers["content-encoding"] == "gzip"


def test_oversized_upload_is_rejected_before_reading(client, settings):
    too_big = b"%PDF" + b"0" * (settings.max_file_bytes + 100 * 1024)
    response = _upload(client, too_big)

    assert response.status_code == 413
    assert response.json() == {"detail": f"The file is larger than {settings.max_file_mb} MB."}
    assert response.headers["X-Frame-Options"] == "DENY"  # security headers apply to early rejections too


def test_sample_brief_includes_action_plan(client):
    brief = client.post("/api/brief/sample").json()

    assert brief["action_plan"]["next_steps"]
    assert brief["action_plan"]["missing_or_unclear"]


def test_sample_brief_never_calls_the_generator(client):
    client.app.dependency_overrides[get_brief_generator] = ExplodingGenerator
    response = client.post("/api/brief/sample")

    assert response.status_code == 200
    brief = response.json()
    assert brief["is_demo"] is True
    assert all(source["verified"] for source in _all_sources(brief))
    assert "not legal advice" in brief["disclaimer"]


def test_upload_in_mock_mode_returns_grounded_brief(client, sample_pdf):
    response = _upload(client, sample_pdf, filename="sample_agreement.pdf")

    assert response.status_code == 200
    brief = response.json()
    assert brief["is_demo"] is False and brief["is_mock"] is True
    assert brief["document"] == {
        "filename": "sample_agreement.pdf",
        "pages": 2,
        "characters": brief["document"]["characters"],
    }
    assert all(source["verified"] for source in _all_sources(brief))


def test_uploaded_filename_is_stripped_of_paths(client, sample_pdf):
    response = _upload(client, sample_pdf, filename="../../secret/offer.pdf")
    assert response.json()["document"]["filename"] == "offer.pdf"


def test_non_pdf_upload_returns_friendly_400(client):
    response = _upload(client, b"hello", filename="notes.txt", content_type="text/plain")
    assert response.status_code == 400
    assert response.json() == {"detail": "Please upload a PDF file."}


def test_missing_file_returns_400(client):
    response = client.post("/api/brief")
    assert response.status_code == 400


def test_non_employment_document_returns_422(client, sample_pdf):
    client.app.dependency_overrides[get_brief_generator] = NotEmploymentGenerator
    response = _upload(client, sample_pdf)

    assert response.status_code == 422
    assert "employment document" in response.json()["detail"]


def test_live_mode_without_key_fails_clearly(client, settings, sample_pdf):
    live = settings.model_copy(update={"llm_mode": "groq", "groq_api_key": ""})
    client.app.dependency_overrides[get_settings] = lambda: live
    response = _upload(client, sample_pdf)

    assert response.status_code == 503
    assert "no API key" in response.json()["detail"]


@pytest.fixture
def limited_client(settings):
    limited = settings.model_copy(update={"rate_limit_requests": 2})
    app = create_app(limited)
    app.dependency_overrides[get_settings] = lambda: limited
    with TestClient(app) as test_client:
        yield test_client


def test_rate_limit_returns_429_after_limit(limited_client):
    statuses = [_upload(limited_client, b"x", content_type="text/plain").status_code for _ in range(3)]

    assert statuses == [400, 400, 429]


def test_sample_endpoint_is_not_rate_limited(limited_client):
    statuses = {limited_client.post("/api/brief/sample").status_code for _ in range(4)}
    assert statuses == {200}


class CrashingGenerator:
    is_mock = False

    def generate(self, pages: list[str]) -> LLMBrief:
        raise RuntimeError("unexpected bug")


def test_unexpected_errors_return_a_generic_500(settings, sample_pdf):
    app = create_app(settings)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_brief_generator] = CrashingGenerator
    with TestClient(app, raise_server_exceptions=False) as test_client:
        response = _upload(test_client, sample_pdf)

    assert response.status_code == 500
    assert response.json() == {"detail": "Something went wrong. Please try again."}  # no internals leaked


def test_missing_sample_returns_503(client, monkeypatch, tmp_path):
    monkeypatch.setattr(api, "SAMPLE_BRIEF_PATH", tmp_path / "missing.json")
    api.load_sample_brief.cache_clear()
    try:
        response = client.post("/api/brief/sample")
    finally:
        api.load_sample_brief.cache_clear()

    assert response.status_code == 503
