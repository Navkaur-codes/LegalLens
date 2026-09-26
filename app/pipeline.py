"""The brief pipeline shared by the API and scripts: generate → check → ground → respond."""

from app.errors import UnsupportedDocumentError
from app.grounding import ground_brief
from app.llm_client import BriefGenerator
from app.pdf_extractor import ExtractedDocument
from app.schemas import BriefResponse, DocumentMeta

NOT_EMPLOYMENT_MESSAGE = (
    "This does not look like an employment document. LegalLens currently supports "
    "offer letters and employment agreements."
)


def build_brief(
    document: ExtractedDocument, filename: str, generator: BriefGenerator, *, is_demo: bool = False
) -> BriefResponse:
    llm_brief = generator.generate(document.pages)
    if not llm_brief.is_employment_document:
        raise UnsupportedDocumentError(NOT_EMPLOYMENT_MESSAGE)

    grounded = ground_brief(llm_brief, document.pages)
    meta = DocumentMeta(filename=filename, pages=document.page_count, characters=document.char_count)
    return BriefResponse(**grounded.model_dump(), document=meta, is_demo=is_demo, is_mock=generator.is_mock)
