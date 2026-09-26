# LegalLens — Personal Legal Brief Generator

> Understand your employment agreement before you sign: a plain-language brief and action plan where every point links back to the page and exact text it came from.

Built for the **PromptWars — Legal Assistance & Access** challenge.

**Live demo:** _add your Render URL here_ · Try **View sample brief** for an instant demo on a fictional agreement.

> **Disclaimer:** LegalLens provides general legal information to help you understand your document. It is not legal advice and does not assess whether any clause is valid or enforceable. For decisions, consult a qualified lawyer or your HR team.

---

## The problem

Employees in India regularly sign offer letters and employment agreements without fully understanding them. Terms such as **notice periods, service bonds, probation, non-compete and non-solicit clauses, confidentiality, IP assignment and transfer clauses** are written in dense legal language. A lawyer is often unaffordable, or feels like overkill, for "just reading an offer letter", so people sign first and discover the terms later, often when changing jobs.

## Who it is for

Employees in India, at any career stage, who are reviewing an offer letter or employment agreement **before signing** or **during employment**.

## What LegalLens does

Upload a text-based PDF and get **one brief in four tabs**:

| Tab | What you get |
|---|---|
| **Overview** | A plain-language summary, the parties, the document type, and key terms (role, pay, start date, probation, notice, leave, location). |
| **Responsibilities & Deadlines** | *Responsibilities stated in your document*: obligations, dates, notice periods and time-bound duties, each with its timing. |
| **Clauses to Review** | Clauses you may want to understand or clarify: what each says, why it may matter, and 2–3 neutral questions you could ask HR or a lawyer. |
| **Action Plan** | A tickable **dates & deadlines checklist**; **missing or unclear information** (e.g. an annexure that is referenced but not included, or an undefined term); **suggested next steps**; and **all questions for HR or a lawyer in one list** with a *Copy questions* button. |

Every finding carries a **source**: page, section and a verbatim quote, plus a badge:

- **✓ Source verified**: the quoted text was found in your document (the page is corrected if the model cited the wrong one).
- **⚠ Source not verified**: the quote or page could not be confirmed.

> Source verification checks that the quoted text appears in your document. It does **not** confirm that the explanation is legally accurate.

You can also:
- try **View sample brief**, a fictional agreement with a pre-generated brief (instant, no API key needed, uses no AI quota);
- print or save the whole brief (all four tabs) as a PDF.

### How it addresses the challenge

| Challenge use case | LegalLens feature |
|---|---|
| Simplifying complex legal documents | Plain-language summary and key-term explanations (Overview) |
| Highlighting important clauses, obligations, risks or inconsistencies | Clauses to Review; Responsibilities & Deadlines; *Missing or unclear information* |
| Generating summaries, checklists or other actionable outputs | Summary, tickable deadlines checklist, suggested next steps, printable brief |
| Helping users understand options and next steps | Suggested next steps (Action Plan) |
| Helping users prepare questions for a legal professional | Per-clause questions, consolidated with one-click copy |
| Providing information, not replacing legal advice | Neutral wording rules, no enforceability verdicts, disclaimer on screen and in print, verified sources |

### Deliberate boundaries

LegalLens explains what a document says. It never calls clauses "risky", "invalid", "unfair" or "unenforceable", never tells you what you "must" do, and never predicts legal outcomes. It declines documents that are not employment-related.

## How it works

```mermaid
flowchart LR
    A[Upload PDF] --> B[Size check<br/>before reading body]
    B --> C[Rate limit<br/>5 per 10 min per IP]
    C --> D[Validate PDF<br/>type · encryption · pages]
    D --> E[Extract text by page<br/>PyMuPDF]
    E --> F[LLM: one call<br/>JSON mode]
    F --> G[Pydantic validation<br/>+ max 1 repair retry]
    G --> H[Employment check]
    H --> I[Grounding<br/>verify every quote]
    I --> J[Brief JSON → 4 tabs]
```

1. **Reject oversized uploads early**, using the declared `Content-Length`, before the body is read.
2. **Validate** the upload: PDF content type and `%PDF` signature, ≤ 5 MB, not password-protected, ≤ 10 pages.
3. **Extract** text page by page with PyMuPDF (ligatures expanded). Fewer than 200 characters means a likely scanned PDF, which is rejected. More than 18,000 characters is rejected.
4. **Generate** the brief with **one** LLM call. The document is wrapped as `<document><page n="1">…</page></document>`, so the model can cite pages and treats the text as data, not instructions.
5. **Validate** the output against Pydantic schemas. Unknown enum values are mapped to `other`, and list lengths are capped. If the JSON is invalid, **one** repair retry is made, then the request fails with a friendly 502.
6. **Ground** every `source` in the brief on the server, wherever it appears. Quote and page text are normalised (Unicode NFKC, curly quotes, dashes, whitespace, case). The cited page is searched first, then all pages. The `verified` flag **does not exist in the model's schema**, so the model can never claim verification.
7. **Render** in the browser using `textContent` only, never `innerHTML`.

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Backend | Python 3.12, **FastAPI**, Uvicorn | Typed, fast, minimal boilerplate; serves the API and the frontend from one service |
| PDF | **PyMuPDF** | Fast, reliable per-page text extraction and validation |
| AI | **Groq** (`openai/gpt-oss-120b`, configurable via `GROQ_MODEL`) | Low-latency inference; JSON mode; low reasoning effort keeps output within budget |
| Validation | **Pydantic v2**, pydantic-settings | One generic schema for LLM output and verified API responses, plus typed config |
| Frontend | HTML, CSS, vanilla JS | No build step; small, fast, accessible |
| Quality | pytest, **ruff** (lint + format), GitHub Actions CI | Offline tests and lint on every push |
| Hosting | Render (single web service) | Free tier, deploys from `render.yaml` |

No database, no user accounts, no frontend framework.

## Project structure

```
app/
  main.py           App factory: routes, static frontend, error handlers
  middleware.py     Early upload-size check, gzip, security headers
  api.py            HTTP routes (orchestration only)
  config.py         Settings and limits, defined once
  schemas.py        Generic Pydantic models (LLM output vs. verified API response)
  errors.py         User-facing error types → HTTP status
  pdf_extractor.py  PDF validation and page-by-page extraction
  prompts.py        System prompt, document delimiting, repair prompt
  llm_client.py     Mock generator (default) and Groq generator (shared client)
  grounding.py      Quote normalisation and verification
  pipeline.py       generate → employment check → ground → response
  rate_limit.py     In-memory per-IP sliding-window limiter
static/
  index.html · styles.css
  js/               ES modules, no build step:
    main.js         entry point: state, upload, loading, event wiring
    api.js          network calls → friendly errors
    brief.js        pure data helpers (unit-tested in Node)
    render.js       Overview, Responsibilities, Clauses, summary panel
    action-plan.js  checklist, next steps, missing info, copy questions
    source.js       verification badge + quote block
    tabs.js         WAI-ARIA tabs
    dom.js          textContent-only DOM helpers
samples/            sample_agreement.pdf (fictional) · sample_brief.json · mock_llm_output.json
scripts/            make_sample_pdf.py · make_sample_brief.py
tests/              pytest suite (offline, no API key) · js/ frontend unit tests (Node)
.github/workflows/  ci.yml: backend (ruff, pytest + coverage) and frontend (node --test) jobs
```

## Run locally

Requires Python 3.11+.

```bash
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

Open **http://localhost:8000**. Use the server address, not `static/index.html` directly.

`requirements.txt` has the exact-pinned runtime dependencies (used by Render). `requirements-dev.txt` adds pytest, httpx and ruff.

### Mock mode vs. live AI

| `LLM_MODE` | Behaviour |
|---|---|
| `mock` (default) | No API calls. Uploads return a fixed placeholder brief for the fictional sample, clearly labelled in the UI as not an analysis of your file. Used for development and tests. |
| `groq` | Live analysis with Groq. Requires `GROQ_API_KEY`. |

For live mode, copy `.env.example` to `.env` and set:

```
LLM_MODE=groq
GROQ_API_KEY=your-key
```

The app never switches from `groq` to `mock` silently. If live mode has no key, it returns a clear error.

### Regenerate the sample files

```bash
python -m scripts.make_sample_pdf      # fictional agreement PDF
python -m scripts.make_sample_brief    # brief JSON (uses LLM_MODE; mock by default = no API call)
```

## Quality checks

```bash
pytest --cov           # 62 backend tests, 100% line and branch coverage (CI fails below 95%)
npm test               # 15 frontend unit tests (Node built-in runner, zero dependencies)
ruff check .           # lint (pycodestyle, pyflakes, isort, bugbear, bandit security rules, …)
ruff format --check .  # formatting
```

The same checks run in GitHub Actions on every push (`.github/workflows/ci.yml`). The frontend's data logic (`static/js/brief.js`) and network error handling (`static/js/api.js`) are DOM-free, so Node tests them directly, including a check that the committed sample brief is fully verified.

The tests use a mock or fake LLM client and make **no network calls**. They cover:
- **PDF validation:** every limit, plus damaged, encrypted and scanned files.
- **Grounding:** normalisation, page correction (including Action Plan sources), and the model being unable to claim verification.
- **API:** the sample never calls the AI, error codes, early 413 for oversized uploads, gzip, security headers, the non-employment check, live mode without a key.
- **Groq client:** JSON mode, reasoning effort, one repair retry, 502 after a second failure, busy and model-not-found messages, a shared connection pool.
- **Prompt construction** and the **rate limiter**.

## Deploy on Render

1. Push this repository to GitHub (single `main` branch).
2. In Render, choose **New → Blueprint** and select the repository. Render reads `render.yaml`.
3. When prompted, set the secret **`GROQ_API_KEY`**. `LLM_MODE=groq` is already set in `render.yaml`.
4. Deploy, then open the service URL and check `/api/health` → `{"status":"ok"}`.
5. Smoke test: click **View sample brief** (no AI call), then upload `samples/sample_agreement.pdf` and confirm a live brief appears with "Source verified" badges.

The start command uses `--proxy-headers`, so the rate limit sees real client IPs behind Render's proxy. On the free plan the service sleeps when idle, so the first request after a pause can take up to about a minute.

## API

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/health` | `{"status": "ok"}` |
| `GET` | `/api/config` | `{"max_file_mb": 5, "max_pages": 10, "max_chars": 18000, "llm_mode": "mock"}` |
| `POST` | `/api/brief` | Multipart field `file` (PDF) → brief. Rate limited. |
| `POST` | `/api/brief/sample` | Pre-generated fictional brief. **Never calls the AI.** |

Response shape (abridged):

```json
{
  "document": {"filename": "offer.pdf", "pages": 2, "characters": 4056},
  "is_demo": false,
  "is_mock": false,
  "is_employment_document": true,
  "overview": {
    "summary": "…", "document_type": "Employment Agreement", "employer": "…", "employee": "…",
    "key_terms": [{"term": "Notice period", "value": "60 days", "explanation": "…",
                   "source": {"page": 1, "section": "8. Notice Period", "quote": "…", "verified": true}}]
  },
  "responsibilities": [{"title": "…", "description": "…", "category": "deadline", "timing": "…", "source": {…}}],
  "clauses_to_review": [{"title": "…", "topic": "bond", "what_it_says": "…", "why_it_matters": "…",
                         "questions_to_ask": ["…"], "source": {…}}],
  "action_plan": {
    "missing_or_unclear": [{"title": "Salary breakdown not included", "detail": "…", "source": {…}}],
    "next_steps": ["Ask HR for Annexure A …"]
  },
  "verification_note": "…",
  "disclaimer": "…"
}
```

Errors always look like `{"detail": "<friendly message>"}`:

| Status | When |
|---|---|
| 400 | Not a PDF, damaged, password-protected, malformed request, or no file |
| 411 | Upload without a declared size |
| 413 | Over 5 MB, over 10 pages, or over 18,000 characters |
| 422 | No extractable text (scanned PDF) or not an employment document |
| 429 | Rate limit reached (5 briefs per 10 minutes per IP) |
| 502 | AI service busy, failed, or returned an unusable response |
| 503 | Live mode enabled without an API key, or sample unavailable |

## Security & privacy

- **Nothing is saved.** No database, and the app never writes uploads anywhere. Files are read, analysed and discarded within the request. (The web framework may temporarily buffer uploads over 1 MB to a temporary file, which is deleted when the request ends.)
- **Oversized uploads are rejected before they are read**, based on `Content-Length`, which prevents large-upload abuse.
- **No document text in logs.** Logs record only status, page and character counts, finding and verified counts, and latency.
- **Secrets stay on the server.** `GROQ_API_KEY` is read from the environment; `.env` is gitignored; the key is never sent to the browser.
- **Input limits** on size, pages and characters, all validated before any AI call, plus **per-IP rate limiting**.
- **Safe rendering.** All model- and document-derived text is inserted with `textContent`.
- **Security headers.** Strict CSP (`default-src 'self'`, no inline scripts), HSTS, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `Cross-Origin-Opener-Policy`, `Cross-Origin-Resource-Policy`, `Permissions-Policy`. They apply to error responses too.
- **Prompt-injection mitigation.** Delimited document text, an explicit "treat as data" rule, and strict schema validation of the output.
- **Generic errors.** No stack traces or provider error details reach the user.
- **Supply chain.** Exact-pinned dependencies; ruff's bandit (`S`) security rules in CI.

## Efficiency

- **One AI call per brief** (at most one repair retry). The sample brief uses **zero** AI calls.
- **Cheap checks first:** size, type, pages and characters are validated before any AI call; oversized bodies are refused before being read.
- **Connection reuse:** one shared Groq client, so HTTP connections are pooled across requests.
- **Bounded output:** a capped token budget with low reasoning effort; list lengths capped by the schema.
- **Gzip** compression for pages and API responses; the static frontend has no framework or build step (about 55 KB uncompressed).
- **Bounded memory:** in-memory rate-limiter entries are purged; the mock fixture and sample brief are parsed once and cached.

## Accessibility

- Semantic HTML landmarks, a skip link, and WAI-ARIA tabs with arrow/Home/End keyboard support and roving tabindex.
- **WCAG AA colour contrast.** Every text/background pair was audited (all ≥ 4.5:1) and the muted grey adjusted where needed.
- Visible focus states; **Windows High Contrast (forced colours)** support for badges, cards and the selected tab.
- Live regions for loading progress and errors; `aria-busy` while a brief is generated; focus moves to the results heading when it loads.
- Text labels on every status badge (colour is never the only signal); labelled checkboxes in the Action Plan.
- A reduced-motion setting, a responsive layout down to phone width, and a print view.

## Assumptions & limitations

- Text-based PDFs only (no OCR). English only.
- Up to **5 MB, 10 pages and 18,000 characters** of text. Long documents are not chunked.
- Designed for Indian employment documents. Explanations are general, not jurisdiction-specific legal analysis.
- AI can make mistakes. Verification confirms that quotes exist, not that explanations are correct.
- The rate limit is in memory: per instance, and reset on restart.
- The Render free tier has cold starts.
- The committed `sample_brief.json` is generated by the full pipeline from the mock generator (a hand-written fixture for the fictional agreement), and it is labelled in the UI as a demonstration result.

## How this maps to the evaluation criteria

| Criterion | Where to look |
|---|---|
| Problem alignment | A specific Indian-employee problem; four outputs covering the challenge's use cases (see the table above) |
| Code quality | Small single-purpose modules (backend and frontend), generic typed schemas, dependency injection, one error hierarchy, handlers that only orchestrate, ruff lint and format |
| Security | Early size rejection, limits, rate limiting, strict headers, safe rendering, no secrets in the repo, pinned dependencies |
| Efficiency | One AI call, checks before the call, pooled connections, gzip, bounded memory, a zero-cost sample |
| Testing | 62 backend tests (100% line + branch coverage) and 15 frontend tests, all offline; CI on every push; a mock LLM mode; injectable dependencies |
| Accessibility | WCAG AA contrast, semantic HTML, ARIA tabs, keyboard support, focus states, forced-colours support, live regions, `aria-busy`, responsive layout, print view |

## Future work

Document Q&A · comparing two offers · OCR for scanned PDFs · Hindi and other Indian languages · longer documents via chunking.

## License

[MIT](LICENSE)
