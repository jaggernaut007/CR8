import os
from unittest.mock import patch

import pytest

from backend.services.file_parser import export_slides_as_images, extract_text


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


# ---------------------------------------------------------------------------
# export_slides_as_images
# ---------------------------------------------------------------------------


class TestExportSlidesAsImages:
    def test_export_pdf_creates_pngs(self, single_slide_pdf, tmp_path):
        out_dir = str(tmp_path / "slides")
        paths = export_slides_as_images(single_slide_pdf, out_dir)
        assert len(paths) >= 1
        for p in paths:
            assert p.endswith(".png")
            assert os.path.exists(p)

    def test_export_pdf_correct_naming(self, single_slide_pdf, tmp_path):
        out_dir = str(tmp_path / "slides")
        paths = export_slides_as_images(single_slide_pdf, out_dir)
        assert "slide_001.png" in os.path.basename(paths[0])

    def test_export_unsupported_raises(self, tmp_path):
        txt_file = str(tmp_path / "notes.txt")
        with open(txt_file, "w") as f:
            f.write("text")
        with pytest.raises(ValueError, match="Unsupported"):
            export_slides_as_images(txt_file, str(tmp_path / "out"))

    def test_path_traversal_rejected(self, single_slide_pdf):
        with pytest.raises(ValueError, match="Path traversal"):
            export_slides_as_images(single_slide_pdf, "/etc/evil_dir")

    def test_pptx_without_libreoffice(self, tmp_path):
        """PPTX export gracefully fails when LibreOffice is not available."""
        pptx_path = str(tmp_path / "test.pptx")
        with open(pptx_path, "wb") as f:
            f.write(b"fake-pptx")

        with patch("backend.services.file_parser.subprocess.run") as mock_run:
            mock_run.return_value = type("Result", (), {
                "returncode": 1, "stderr": b"command not found"
            })()
            with pytest.raises(RuntimeError, match="LibreOffice"):
                export_slides_as_images(pptx_path, str(tmp_path / "out"))

    def test_export_creates_output_dir(self, single_slide_pdf, tmp_path):
        out_dir = str(tmp_path / "nested" / "slides")
        paths = export_slides_as_images(single_slide_pdf, out_dir)
        assert os.path.isdir(out_dir)
        assert len(paths) >= 1

    def test_export_widescreen_pdf_produces_1080p(self, tmp_path):
        """144 DPI on 13.333x7.5 inch widescreen slides must produce 1920x1080."""
        import pymupdf
        try:
            from PIL import Image
        except ImportError:
            pytest.skip("Pillow not installed")

        # Create a synthetic widescreen PDF (13.333" x 7.5" = 960pt x 540pt)
        pdf_path = str(tmp_path / "widescreen.pdf")
        doc = pymupdf.open()
        doc.new_page(width=960, height=540)  # 13.333in * 72pt/in, 7.5in * 72pt/in
        doc.save(pdf_path)
        doc.close()

        out_dir = str(tmp_path / "slides_1080p")
        paths = export_slides_as_images(pdf_path, out_dir, dpi=144)
        assert len(paths) == 1
        with Image.open(paths[0]) as img:
            assert img.size == (1920, 1080), f"Expected 1920x1080, got {img.size}"
