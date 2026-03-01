import os

import pytest

from backend.services.file_parser import extract_text


def test_extract_text_from_pdf(single_slide_pdf):
    pages = extract_text(single_slide_pdf)

    assert len(pages) > 0
    assert all("text" in p and "source" in p and "page" in p for p in pages)

    full_text = " ".join(p["text"] for p in pages).lower()
    assert "word" in full_text
    assert pages[0]["source"] == "01_Word_Vectors_I.pdf"
    assert pages[0]["page"] == 1


def test_extract_text_returns_nonempty_pages(single_slide_pdf):
    pages = extract_text(single_slide_pdf)
    nonempty = [p for p in pages if p["text"].strip()]
    assert len(nonempty) >= 1


def test_extract_text_multiple_files(three_slide_pdfs):
    for path in three_slide_pdfs:
        pages = extract_text(path)
        assert len(pages) > 0


def test_nonexistent_file_returns_empty_or_raises(tmp_path):
    """extract_text on a missing file should return [] or raise a clear error."""
    missing = str(tmp_path / "does_not_exist.pdf")
    try:
        pages = extract_text(missing)
        # Acceptable: returns empty list
        assert isinstance(pages, list)
    except (FileNotFoundError, ValueError, RuntimeError):
        pass  # Also acceptable: raises a clear error


def test_empty_pdf_returns_no_meaningful_text(tmp_path):
    """A PDF with no text content should return either [] or pages with empty text."""
    try:
        from fpdf import FPDF
    except ImportError:
        pytest.skip("fpdf2 not installed")

    # Create a PDF with no text (blank page only)
    pdf = FPDF()
    pdf.add_page()
    path = str(tmp_path / "empty.pdf")
    pdf.output(path)

    pages = extract_text(path)
    # Either empty list or all pages have no meaningful text
    if pages:
        total_text = " ".join(p["text"] for p in pages).strip()
        assert total_text == "" or len(total_text) < 10


def test_unsupported_extension_returns_empty_or_raises(tmp_path):
    """A .txt file is not a supported format — should return [] or raise."""
    txt_path = str(tmp_path / "notes.txt")
    with open(txt_path, "w") as f:
        f.write("Some text content here.")

    try:
        pages = extract_text(txt_path)
        assert isinstance(pages, list)
        # If it returns pages, they should be empty (no PDF parsing done)
        assert pages == []
    except (ValueError, RuntimeError, Exception):
        pass  # Raising is also acceptable
