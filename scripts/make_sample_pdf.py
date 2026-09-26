"""Generate samples/sample_agreement.pdf: a FICTIONAL Indian employment agreement for demos and tests.

Run from the project root:  python -m scripts.make_sample_pdf
"""

import html
import io

import pymupdf

from app.config import SAMPLE_PDF_PATH

FICTIONAL_LABEL = "FICTIONAL DEMONSTRATION DOCUMENT - NOT A REAL AGREEMENT"

TITLE = "Employment Agreement"
INTRO = (
    "This Employment Agreement is made on 10 June 2026 between Example Technologies Private Limited, "
    'a fictional company with its office in Bengaluru, Karnataka (the "Company"), and A. Sample '
    '(the "Employee"). All names and details in this document are invented for demonstration purposes.'
)

CLAUSES = [
    (
        "1. Position and Start Date",
        "The Employee is appointed as Software Engineer in the Product Engineering team. "
        "The Employee shall join the Company on 1 July 2026 at the Bengaluru office.",
    ),
    (
        "2. Compensation",
        "The Employee shall receive a total cost to company of INR 9,00,000 per annum, payable monthly "
        "after applicable deductions. The detailed salary structure is set out in Annexure A. "
        "Any performance bonus is at the sole discretion of the Company.",
    ),
    (
        "3. Probation",
        "The Employee shall be on probation for a period of six months from the date of joining. "
        "The Company may extend the probation period by up to three months at its discretion. "
        "During probation, either party may terminate this Agreement by giving 15 days written notice.",
    ),
    (
        "4. Working Hours and Location",
        "The normal working hours are nine hours per day, including a one hour break, five days a week. "
        "The Employee may be required to work additional hours when business needs require. "
        "The Company may transfer the Employee to any of its offices or client locations in India.",
    ),
    (
        "5. Leave",
        "The Employee is entitled to 18 days of paid leave per calendar year, credited on a pro-rata basis. "
        "Unused leave may be carried forward up to a maximum of 30 days.",
    ),
    (
        "6. Joining Formalities",
        "The Employee shall submit copies of educational certificates, previous employment relieving letters "
        "and identity documents within 7 days of joining. "
        "The appointment is subject to satisfactory background verification.",
    ),
    (
        "7. Service Bond",
        "The Employee agrees to serve the Company for a minimum period of 24 months from the date of joining. "
        "If the Employee resigns before completing 24 months, the Employee shall pay the Company "
        "INR 1,50,000 towards training costs, reduced proportionately for the months already served.",
    ),
    (
        "8. Notice Period and Resignation",
        "After confirmation, either party may terminate this Agreement by giving 60 days written notice. "
        "The Company may, at its sole discretion, accept payment of basic salary in lieu of the notice period. "
        "The Company may terminate this Agreement without notice in case of misconduct.",
    ),
    (
        "9. Confidentiality",
        "The Employee shall keep all confidential information of the Company and its clients strictly confidential "
        "during employment and for a period of three years after leaving the Company.",
    ),
    (
        "10. Intellectual Property",
        "All inventions, software, designs and other work created by the Employee during the period of employment, "
        "whether or not during working hours, shall belong exclusively to the Company.",
    ),
    (
        "11. Other Employment",
        "The Employee shall not take up any other employment, business or paid work, including part-time "
        "or freelance work, without the prior written consent of the Company.",
    ),
    (
        "12. Non-Compete and Non-Solicitation",
        "For a period of 12 months after leaving the Company, the Employee shall not join or work for any "
        "competitor of the Company in India. For the same period, the Employee shall not solicit any employee "
        "or client of the Company.",
    ),
    (
        "13. Return of Property and Final Settlement",
        "On the last working day, the Employee shall return the laptop, access card and all other Company property. "
        "The full and final settlement shall be processed within 45 days of the last working day.",
    ),
    (
        "14. Governing Law",
        "This Agreement is governed by the laws of India. The courts at Bengaluru shall have exclusive jurisdiction.",
    ),
    (
        "15. Acceptance",
        "Please sign and return a copy of this Agreement within 5 days of the date of this Agreement "
        "to confirm your acceptance.",
    ),
]

CSS = """
body { font-family: sans-serif; font-size: 10.5pt; line-height: 1.45; }
h1 { font-size: 16pt; text-align: center; margin-bottom: 6pt; }
h2 { font-size: 11.5pt; margin-top: 10pt; margin-bottom: 2pt; }
p { margin-top: 0; margin-bottom: 4pt; text-align: left; }
"""


def build_html() -> str:
    parts = [f"<h1>{html.escape(TITLE)}</h1>", f"<p>{html.escape(INTRO)}</p>"]
    for heading, text in CLAUSES:
        parts.append(f"<h2>{html.escape(heading)}</h2><p>{html.escape(text)}</p>")
    parts.append(
        "<h2>Signatures</h2><p>For Example Technologies Private Limited: ____________</p>"
        "<p>Employee (A. Sample): ____________</p>"
    )
    return "".join(parts)


def render_pdf() -> bytes:
    """Lay out the agreement with pymupdf.Story, then stamp the fictional label on every page."""
    story = pymupdf.Story(html=build_html(), user_css=CSS)
    mediabox = pymupdf.paper_rect("a4")
    content_area = mediabox + (60, 72, -60, -72)
    raw = io.BytesIO()
    writer = pymupdf.DocumentWriter(raw)
    more = True
    while more:
        device = writer.begin_page(mediabox)
        more, _ = story.place(content_area)
        story.draw(device)
        writer.end_page()
    writer.close()

    with pymupdf.open(stream=raw.getvalue(), filetype="pdf") as doc:
        for number, page in enumerate(doc, start=1):
            page.insert_text((60, 40), FICTIONAL_LABEL, fontsize=8.5, fontname="hebo", color=(0.6, 0.1, 0.1))
            footer = f"{FICTIONAL_LABEL}  |  Page {number} of {doc.page_count}"
            page.insert_text((60, mediabox.height - 36), footer, fontsize=8, fontname="helv", color=(0.4, 0.4, 0.4))
        return doc.tobytes(garbage=3, deflate=True)


def main() -> None:
    SAMPLE_PDF_PATH.parent.mkdir(parents=True, exist_ok=True)
    SAMPLE_PDF_PATH.write_bytes(render_pdf())
    with pymupdf.open(SAMPLE_PDF_PATH) as doc:
        chars = sum(len(page.get_text("text")) for page in doc)
        print(f"Wrote {SAMPLE_PDF_PATH} ({doc.page_count} pages, ~{chars} characters)")


if __name__ == "__main__":
    main()
