"""HTTP routes. Handlers only orchestrate; the work lives in the pipeline modules."""

import logging
import time
from functools import lru_cache
from pathlib import PurePath

from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import ValidationError

from app.config import SAMPLE_BRIEF_PATH, Settings, get_settings
from app.errors import SampleUnavailableError
from app.llm_client import BriefGenerator, get_brief_generator
from app.pdf_extractor import extract_pdf
from app.pipeline import build_brief
from app.rate_limit import enforce_rate_limit
from app.schemas import BriefResponse, ClientConfig

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

_MAX_FILENAME_CHARS = 120


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/config", response_model=ClientConfig)
def client_config(settings: Settings = Depends(get_settings)) -> ClientConfig:
    return ClientConfig(
        max_file_mb=settings.max_file_mb,
        max_pages=settings.max_pages,
        max_chars=settings.max_chars,
        llm_mode=settings.llm_mode,
    )


@router.post("/brief", response_model=BriefResponse, dependencies=[Depends(enforce_rate_limit)])
def create_brief(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
    generator: BriefGenerator = Depends(get_brief_generator),
) -> BriefResponse:
    """Analyse an uploaded PDF. The file is read into memory and never stored."""
    started = time.perf_counter()
    data = file.file.read(settings.max_file_bytes + 1)
    document = extract_pdf(data, file.content_type, settings)
    filename = PurePath(file.filename or "document.pdf").name[:_MAX_FILENAME_CHARS]

    brief = build_brief(document, filename, generator)
    findings = brief.findings()
    logger.info(
        "brief generated pages=%d chars=%d findings=%d verified=%d ms=%d",
        document.page_count,
        document.char_count,
        len(findings),
        sum(finding.source.verified for finding in findings),
        (time.perf_counter() - started) * 1000,
    )
    return brief


@router.post("/brief/sample", response_model=BriefResponse)
def sample_brief() -> BriefResponse:
    """Return the committed demo brief for the fictional sample. Never calls the AI service."""
    return load_sample_brief()


@lru_cache
def load_sample_brief() -> BriefResponse:
    try:
        return BriefResponse.model_validate_json(SAMPLE_BRIEF_PATH.read_text(encoding="utf-8"))
    except (OSError, ValidationError) as exc:
        logger.error("Sample brief unavailable: %s", type(exc).__name__)
        raise SampleUnavailableError("The sample brief is not available right now.") from exc
