# Documents Module

This module handles **evidence document uploads** (PDF/images with text extraction and embeddings) and **generated court document PDFs** produced from the Drafting Agent output.

## Generated Court Document PDFs

Three specialized generators turn `GeneratedDocument` text content (stored by the Drafting Agent) into formatted PDFs suitable for Minnesota Conciliation Court:

| Module | Purpose |
|--------|--------|
| `statement_of_claim.py` | Statement of Claim with court header, parties, claim amount, facts, legal basis, relief requested, signature block |
| `hearing_script.py` | Hearing script with introduction, key points, evidence order, closing statement |
| `advice_generator.py` | Legal guidance document with case summary, strengths/weaknesses, recommended actions, procedural guidance, disclaimer |

Formatting follows Minnesota Conciliation Court conventions: consistent headers, 12pt body text, 1-inch margins, page numbers in footer. ReportLab is used for layout.

### JSON content structure expected by each generator

**Statement of Claim** (`statement_of_claim`):

- `title`, `parties` (plaintiff/defendant), `claim_amount`, `county`
- `facts_section`, `legal_basis_section`, `relief_requested`
- `full_text` — used as fallback when JSON is missing or invalid

**Hearing Script** (`hearing_script`):

- `introduction`, `key_points` (list), `evidence_presentation_order` (list), `closing_statement`
- `full_text` — fallback

**Legal Advice** (`legal_advice`):

- `case_summary`, `strengths_and_weaknesses`, `recommended_actions` (list), `procedural_guidance`
- `full_text` — fallback

If the stored `content` is not valid JSON or fields are missing, each generator falls back to rendering `full_text` or "No content." so that PDF generation does not fail.

### API endpoints for PDF generation and download

- **POST** `/api/documents/generated/{document_id}/generate-pdf` — Generate PDF for a generated document; updates `file_path` and returns `DocumentGenerationResponse` with `generation_time_ms`.
- **GET** `/api/documents/generated/{document_id}/download` — Download the PDF (attachment). Returns 404 if PDF has not been generated yet.
- **GET** `/api/documents/cases/{case_id}/generated` — List all generated documents for a case (ordered by `generated_at` desc), with `has_pdf` and `download_url` for frontend convenience.
- **POST** `/api/documents/generated/{document_id}/regenerate` — Create a new version of the document and generate its PDF; previous version remains for history.
- **DELETE** `/api/documents/generated/{document_id}` — Delete the generated document record and its PDF file (if any).

All endpoints require authentication and verify that the user owns the case.

### Troubleshooting

- **PDF not created / 404 on download** — Call `POST .../generate-pdf` first; the Drafting Agent only stores text content.
- **Empty or malformed PDF** — Check that `GeneratedDocument.content` is valid JSON with the expected keys, or that `full_text` is present for fallback.
- **ReportLab errors** — Ensure `reportlab` is installed (`requirements.txt`). Font issues on headless servers may require system fonts or ReportLab’s built-in fonts only.
- **File permission errors** — Ensure `GENERATED_DOCS_DIR` (default `./uploads/generated`) exists and is writable; the app creates it on startup.

### ReportLab styling and customization

Shared layout and styles live in `templates.py`:

- `create_mn_court_header()` — Court header on each page
- `create_footer_with_page_numbers()` — Page numbers in footer
- `get_court_document_styles()` — ParagraphStyle for title, section headers, body, signature, disclaimer, notes
- Helpers: `format_party_names()`, `format_currency()`, `add_signature_block()`, `safe_parse_json_content()`

Constants such as margins, font name, and font size are defined in `templates.py`; override or extend styles there to change the look of all generated court documents.
