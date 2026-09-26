"""Shared fixtures. Tests never touch the network or need a Groq key."""

from collections.abc import Callable, Iterator

import pymupdf
import pytest
from fastapi.testclient import TestClient

from app.config import MOCK_LLM_OUTPUT_PATH, SAMPLE_PDF_PATH, Settings, get_settings
from app.main import create_app
from app.schemas import LLMBrief


@pytest.fixture
def settings() -> Settings:
    return Settings(_env_file=None, llm_mode="mock", groq_api_key="")


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    app = create_app(settings)
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def make_pdf() -> Callable[..., bytes]:
    """Build a PDF in memory: one page per string (empty string = blank page)."""

    def _make(pages: list[str], *, encrypt: bool = False) -> bytes:
        doc = pymupdf.open()
        for text in pages:
            page = doc.new_page()
            if text:
                page.insert_textbox(pymupdf.Rect(40, 40, 555, 800), text, fontsize=8)
        options = {"encryption": pymupdf.PDF_ENCRYPT_AES_256, "user_pw": "user", "owner_pw": "owner"} if encrypt else {}
        return doc.tobytes(**options)

    return _make


@pytest.fixture
def sample_pdf() -> bytes:
    return SAMPLE_PDF_PATH.read_bytes()


@pytest.fixture
def mock_brief() -> LLMBrief:
    return LLMBrief.model_validate_json(MOCK_LLM_OUTPUT_PATH.read_text(encoding="utf-8"))
