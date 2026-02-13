"""
Tests for OCR module.
Run against a sample 1-page PDF to verify Gemini Vision output quality.
"""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

# Skip entire module if no API key
pytestmark = pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEYS") and not os.getenv("GEMINI_API_KEY"),
    reason="GEMINI_API_KEYS not set",
)


def _make_simple_pdf() -> bytes:
    """Create a minimal valid PDF with Thai text for testing."""
    # Use PyMuPDF to create a test PDF
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (50, 100),
        "ระเบียบกระทรวงการคลัง\nว่าด้วยการจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ\nพ.ศ. 2560",
        fontsize=12,
    )
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_ocr_native_text():
    """PDF with embedded text should use native extraction, not OCR."""
    from src.ingestion.ocr import pdf_to_text

    pdf_bytes = _make_simple_pdf()
    text = pdf_to_text(pdf_bytes, file_id="test_native_001", force=True)

    assert isinstance(text, str)
    assert len(text) > 0
    # Should contain Thai text
    assert any(c > "\u0e00" for c in text), "Expected Thai characters in output"


def test_ocr_caches_result(tmp_path, monkeypatch):
    """Second call with same file_id should use cache."""
    import src.config as config

    monkeypatch.setattr(config, "OCR_CACHE_DIR", tmp_path)

    from src.ingestion import ocr as ocr_module

    monkeypatch.setattr(ocr_module, "OCR_CACHE_DIR", tmp_path)

    pdf_bytes = _make_simple_pdf()
    file_id = "test_cache_001"

    # First call
    result1 = ocr_module.pdf_to_text(pdf_bytes, file_id=file_id, force=True)

    # Second call — should hit cache
    result2 = ocr_module.pdf_to_text(pdf_bytes, file_id=file_id, force=False)

    assert result1 == result2


def test_ocr_output_has_page_markers():
    """Output should include page markers."""
    from src.ingestion.ocr import pdf_to_text

    pdf_bytes = _make_simple_pdf()
    text = pdf_to_text(pdf_bytes, file_id="test_markers_001", force=True)

    assert "<!-- page 1" in text
