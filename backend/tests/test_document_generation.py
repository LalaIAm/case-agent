"""
Tests for generated document PDF generators (statement of claim, hearing script, legal advice).
"""
import json
import tempfile
from pathlib import Path
from uuid import uuid4

import pytest

from backend.documents.statement_of_claim import generate_statement_of_claim_pdf
from backend.documents.hearing_script import generate_hearing_script_pdf
from backend.documents.advice_generator import generate_advice_pdf


def _make_mock_generated_doc(content: str, document_type: str = "statement_of_claim"):
    """Create a minimal mock GeneratedDocument for generator tests."""
    mock = type("GeneratedDocument", (), {})()
    mock.id = uuid4()
    mock.case_id = uuid4()
    mock.content = content
    mock.document_type = document_type
    mock.file_path = None
    mock.version = 1
    return mock


def test_statement_of_claim_generation():
    """Generate Statement of Claim PDF from valid JSON content; verify file created and size > 0."""
    content = json.dumps({
        "title": "Statement of Claim",
        "parties": {"plaintiff": "Jane Doe", "defendant": "John Smith"},
        "claim_amount": 1500.00,
        "county": "Hennepin",
        "facts_section": "The defendant failed to return the security deposit.",
        "legal_basis_section": "Minn. Stat. § 504B.178",
        "relief_requested": "Judgment for $1,500 plus costs.",
        "full_text": "Full text fallback.",
    })
    mock_doc = _make_mock_generated_doc(content, "statement_of_claim")
    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp) / "statement_of_claim.pdf"
        result = generate_statement_of_claim_pdf(mock_doc, str(output))
        assert result == str(output)
        assert output.exists()
        assert output.stat().st_size > 0


def test_hearing_script_generation():
    """Generate Hearing Script PDF from valid JSON content; verify file created and size > 0."""
    content = json.dumps({
        "introduction": "Your Honor, I am the plaintiff in this matter.",
        "key_points": ["Breach of contract", "Damages of $1,500"],
        "evidence_presentation_order": ["Lease agreement", "Photos"],
        "closing_statement": "I request judgment in my favor.",
        "full_text": "Full script text.",
    })
    mock_doc = _make_mock_generated_doc(content, "hearing_script")
    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp) / "hearing_script.pdf"
        result = generate_hearing_script_pdf(mock_doc, str(output))
        assert result == str(output)
        assert output.exists()
        assert output.stat().st_size > 0


def test_advice_generation():
    """Generate Legal Advice PDF from valid JSON content; verify file created and size > 0."""
    content = json.dumps({
        "case_summary": "Small claims dispute over security deposit.",
        "strengths_and_weaknesses": "Strong documentation; defendant may dispute amounts.",
        "recommended_actions": ["File Statement of Claim", "Bring copies to hearing"],
        "procedural_guidance": "Serve the defendant at least 14 days before hearing.",
        "full_text": "Full guidance text.",
    })
    mock_doc = _make_mock_generated_doc(content, "legal_advice")
    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp) / "advice.pdf"
        result = generate_advice_pdf(mock_doc, str(output))
        assert result == str(output)
        assert output.exists()
        assert output.stat().st_size > 0


def test_malformed_json_handling():
    """Generators with invalid JSON content should fall back to full_text rendering and not raise."""
    # Invalid JSON - no valid object
    mock_soc = _make_mock_generated_doc("not valid json {{{", "statement_of_claim")
    mock_script = _make_mock_generated_doc("not valid json [", "hearing_script")
    mock_advice = _make_mock_generated_doc("not valid json", "legal_advice")

    with tempfile.TemporaryDirectory() as tmp:
        out1 = Path(tmp) / "soc.pdf"
        out2 = Path(tmp) / "script.pdf"
        out3 = Path(tmp) / "advice.pdf"
        generate_statement_of_claim_pdf(mock_soc, str(out1))
        generate_hearing_script_pdf(mock_script, str(out2))
        generate_advice_pdf(mock_advice, str(out3))
        assert out1.exists() and out1.stat().st_size > 0
        assert out2.exists() and out2.stat().st_size > 0
        assert out3.exists() and out3.stat().st_size > 0


def test_missing_fields_handling():
    """Partial JSON structures should result in graceful degradation (no exception)."""
    content_minimal = json.dumps({"full_text": "Only full text is present."})
    mock_doc = _make_mock_generated_doc(content_minimal, "statement_of_claim")
    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp) / "minimal.pdf"
        generate_statement_of_claim_pdf(mock_doc, str(output))
        assert output.exists()
        assert output.stat().st_size > 0

    content_empty_obj = json.dumps({})
    mock_doc2 = _make_mock_generated_doc(content_empty_obj, "hearing_script")
    with tempfile.TemporaryDirectory() as tmp:
        output2 = Path(tmp) / "empty.pdf"
        generate_hearing_script_pdf(mock_doc2, str(output2))
        assert output2.exists()
