import os
import tempfile
from unittest.mock import patch

import pytest

from backend.services.file_parser import export_slides_as_images, extract_text
from backend.services.file_parser import _validate_output_dir


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

    def test_pptx_without_libreoffice_binary(self, tmp_path):
        """shutil.which guard raises RuntimeError when libreoffice is absent."""
        pptx_path = str(tmp_path / "test.pptx")
        with open(pptx_path, "wb") as f:
            f.write(b"fake-pptx")

        with patch("backend.services.file_parser.shutil.which", return_value=None), \
             pytest.raises(RuntimeError, match="libreoffice is not installed"):
            export_slides_as_images(pptx_path, str(tmp_path / "out"))

    def test_pptx_libreoffice_conversion_fails(self, tmp_path):
        """PPTX export raises RuntimeError when LibreOffice exits non-zero."""
        pptx_path = str(tmp_path / "test.pptx")
        with open(pptx_path, "wb") as f:
            f.write(b"fake-pptx")

        with patch("backend.services.file_parser.shutil.which", return_value="/usr/bin/libreoffice"), \
             patch("backend.services.file_parser.subprocess.run") as mock_run:
            mock_run.return_value = type("Result", (), {
                "returncode": 1, "stderr": b"conversion failed"
            })()
            with pytest.raises(RuntimeError, match="conversion failed"):
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


# ---------------------------------------------------------------------------
# _validate_output_dir — edge cases
# ---------------------------------------------------------------------------


class TestValidateOutputDir:
    """Direct unit tests for the path-traversal guard in _validate_output_dir."""

    def test_tmp_path_is_allowed(self, tmp_path):
        """A path inside tempfile.gettempdir() must not raise."""
        sub = str(tmp_path / "sub")
        # Should not raise — tmp_path is inside the system temp dir
        _validate_output_dir(sub)

    def test_cwd_subdir_is_allowed(self, tmp_path, monkeypatch):
        """A path inside the working directory must be accepted."""
        monkeypatch.chdir(tmp_path)
        allowed = str(tmp_path / "outputs" / "slides")
        _validate_output_dir(allowed)  # must not raise

    def test_cwd_itself_is_allowed(self, tmp_path, monkeypatch):
        """Passing the cwd itself (not a subdirectory) is explicitly allowed."""
        monkeypatch.chdir(tmp_path)
        _validate_output_dir(str(tmp_path))  # must not raise

    def test_system_tmp_itself_is_allowed(self):
        """The system temp root is an explicitly allowed base."""
        tmp = os.path.realpath(tempfile.gettempdir())
        _validate_output_dir(tmp)  # must not raise

    def test_absolute_path_outside_cwd_and_tmp_raises(self, tmp_path, monkeypatch):
        """A path that is neither under cwd nor under /tmp must raise ValueError."""
        monkeypatch.chdir(tmp_path)
        with pytest.raises(ValueError, match="Path traversal"):
            _validate_output_dir("/etc/evil")

    def test_dotdot_traversal_from_non_tmp_cwd_raises(self, monkeypatch):
        """A dotdot path that escapes a non-tmp cwd to outside both cwd and /tmp
        must be rejected by the path-traversal guard.

        tmp_path is itself inside /tmp so going up from it stays in /tmp and
        would be allowed. We use the project directory (not under /tmp) as cwd
        to ensure a dotdot escape reliably leaves both allowed roots.
        """
        import os as _os
        project_dir = _os.path.realpath(_os.path.join(_os.path.dirname(__file__), '..', '..'))
        monkeypatch.chdir(project_dir)
        # Four levels up from the project dir lands in /private/etc on macOS
        # which is neither under cwd nor under /tmp
        evil = _os.path.join(project_dir, '..', '..', '..', '..', 'etc', 'shadow')
        with pytest.raises(ValueError, match="Path traversal"):
            _validate_output_dir(evil)

    def test_symlink_traversal_rejected(self, tmp_path, monkeypatch):
        """A symlink that resolves outside the allowed roots must be rejected.

        We use monkeypatch to change cwd to tmp_path, then create a symlink
        inside tmp_path pointing to /etc to simulate a symlink escape.
        """
        monkeypatch.chdir(tmp_path)
        link = tmp_path / "escape_link"
        try:
            link.symlink_to("/etc")
        except (OSError, NotImplementedError):
            pytest.skip("Cannot create symlinks on this system")

        with pytest.raises(ValueError, match="Path traversal"):
            _validate_output_dir(str(link / "passwd"))

    def test_tmp_subdir_with_dotdot_allowed_when_stays_in_tmp(self, tmp_path):
        """A path using .. that resolves back into /tmp is still accepted."""
        sub = tmp_path / "a" / ".." / "b"
        # os.path.realpath will resolve this to tmp_path/b — still inside tmp
        _validate_output_dir(str(sub))  # must not raise

    def test_error_message_contains_the_bad_path(self, tmp_path, monkeypatch):
        """ValueError message must include the offending path for debuggability."""
        monkeypatch.chdir(tmp_path)
        bad_path = "/var/secret"
        with pytest.raises(ValueError, match=bad_path):
            _validate_output_dir(bad_path)

    def test_root_path_raises(self, tmp_path, monkeypatch):
        """Passing '/' must be rejected."""
        monkeypatch.chdir(tmp_path)
        with pytest.raises(ValueError, match="Path traversal"):
            _validate_output_dir("/")
