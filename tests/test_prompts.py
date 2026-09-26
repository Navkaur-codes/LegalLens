from app.prompts import SYSTEM_PROMPT, build_messages, build_repair_message, format_document


def test_document_is_delimited_with_page_numbers():
    text = format_document(["first page", "second page"])

    assert text.startswith("<document>") and text.endswith("</document>")
    assert '<page n="1">\nfirst page\n</page>' in text
    assert '<page n="2">\nsecond page\n</page>' in text


def test_messages_put_rules_in_system_and_document_in_user():
    system, user = build_messages(["page text"])

    assert system["role"] == "system" and system["content"] == SYSTEM_PROMPT
    assert user["role"] == "user" and '<page n="1">' in user["content"]


def test_system_prompt_encodes_legal_boundaries_and_injection_defence():
    for rule in ("Never give legal advice", "untrusted data", "VERBATIM quote", "action_plan", "missing_or_unclear"):
        assert rule in SYSTEM_PROMPT


def test_repair_message_truncates_long_errors():
    message = build_repair_message("x" * 10_000)
    assert message["role"] == "user"
    assert len(message["content"]) < 2_000
