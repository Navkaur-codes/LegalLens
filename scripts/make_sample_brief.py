"""Generate samples/sample_brief.json from the fictional sample PDF using the real pipeline.

Uses LLM_MODE from the environment/.env: mock (default, no API call) or groq (ONE live call).
Run from the project root:  python -m scripts.make_sample_brief
"""

from app.config import SAMPLE_BRIEF_PATH, SAMPLE_PDF_PATH, get_settings
from app.llm_client import get_brief_generator
from app.pdf_extractor import extract_pdf
from app.pipeline import build_brief


def main() -> None:
    settings = get_settings()
    document = extract_pdf(SAMPLE_PDF_PATH.read_bytes(), "application/pdf", settings)
    brief = build_brief(document, SAMPLE_PDF_PATH.name, get_brief_generator(settings), is_demo=True)
    SAMPLE_BRIEF_PATH.write_text(brief.model_dump_json(indent=2) + "\n", encoding="utf-8")

    findings = brief.findings()
    verified = sum(finding.source.verified for finding in findings)
    print(f"Wrote {SAMPLE_BRIEF_PATH} using LLM_MODE={settings.llm_mode}: {verified}/{len(findings)} sources verified")


if __name__ == "__main__":
    main()
