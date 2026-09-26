from app.grounding import ground_brief, normalize, normalize_pages, verify_source
from app.pdf_extractor import extract_pdf
from app.schemas import CitedSource, LLMBrief

PAGES = normalize_pages(
    [
        "1. Probation\nThe Employee shall be on probation for a period of six months.",
        "8. Notice\nAfter confirmation, either party may give 60 days written notice.",
    ]
)


def test_normalize_handles_ligatures_quotes_dashes_and_spacing():
    assert normalize("  Conﬁdential “Info” — 3 years\n") == 'confidential "info" - 3 years'


def test_quote_on_cited_page_is_verified():
    source = verify_source(CitedSource(page=1, quote="on probation for a period of six months"), PAGES)
    assert source.verified and source.page == 1


def test_quote_with_different_case_whitespace_and_quotes_is_verified():
    source = verify_source(CitedSource(page=2, quote="“After  CONFIRMATION, either party”"), PAGES)
    assert source.verified


def test_wrong_page_is_corrected_when_quote_found_elsewhere():
    source = verify_source(CitedSource(page=1, section="8. Notice", quote="60 days written notice"), PAGES)
    assert source.verified and source.page == 2 and source.section == "8. Notice"


def test_missing_quote_is_not_verified_and_not_replaced():
    source = verify_source(CitedSource(page=1, quote="a 90 day notice period applies"), PAGES)
    assert not source.verified
    assert source.page == 1 and source.quote == "a 90 day notice period applies"


def test_empty_or_null_quote_is_not_verified():
    assert not verify_source(CitedSource(page=1, quote=None), PAGES).verified
    assert not verify_source(CitedSource(page=1, quote=" ... "), PAGES).verified


def test_out_of_range_page_still_searches_all_pages():
    source = verify_source(CitedSource(page=99, quote="six months"), PAGES)
    assert source.verified and source.page == 1


def test_model_cannot_claim_verification(mock_brief, sample_pdf, settings):
    data = mock_brief.model_dump()
    data["overview"]["key_terms"][0]["source"] = {"page": 1, "quote": "invented text", "verified": True}
    brief = LLMBrief.model_validate(data)

    grounded = ground_brief(brief, extract_pdf(sample_pdf, "application/pdf", settings).pages)
    assert grounded.overview.key_terms[0].source.verified is False


def test_all_mock_fixture_quotes_ground_against_sample_pdf(mock_brief, sample_pdf, settings):
    grounded = ground_brief(mock_brief, extract_pdf(sample_pdf, "application/pdf", settings).pages)
    findings = grounded.findings()

    assert grounded.action_plan.missing_or_unclear  # the action plan is grounded too
    assert len(findings) == len(mock_brief.findings())
    assert all(finding.source.verified for finding in findings)


def test_action_plan_sources_get_page_correction():
    brief = LLMBrief.model_validate(
        {
            "is_employment_document": True,
            "overview": {"summary": "An agreement."},
            "action_plan": {
                "missing_or_unclear": [
                    {"title": "Notice", "detail": "Detail.", "source": {"page": 1, "quote": "60 days written notice"}}
                ],
                "next_steps": ["Ask HR."],
            },
        }
    )
    grounded = ground_brief(brief, ["Probation of six months.", "Either party may give 60 days written notice."])

    source = grounded.action_plan.missing_or_unclear[0].source
    assert source.verified and source.page == 2
