import pytest
from pathlib import Path


@pytest.fixture
def single_slide_pdf(tmp_path):
    """Generate a minimal test PDF with known content."""
    try:
        from fpdf import FPDF
    except ImportError:
        pytest.skip("fpdf2 not installed")

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=16)
    pdf.cell(text="Word Vectors and Embeddings")
    pdf.ln(12)
    pdf.set_font("Helvetica", size=12)
    pdf.multi_cell(w=0, text="This lecture covers word vector representations and neural network approaches to NLP.")

    path = tmp_path / "01_Word_Vectors_I.pdf"
    pdf.output(str(path))
    return str(path)


@pytest.fixture
def three_slide_pdfs(tmp_path):
    """Generate three minimal test PDFs."""
    try:
        from fpdf import FPDF
    except ImportError:
        pytest.skip("fpdf2 not installed")

    titles = [
        ("01_Word_Vectors_I.pdf", "Word Vectors and Embeddings"),
        ("08_Transformers.pdf", "Transformer Architecture"),
        ("09_Pretraining.pdf", "Pretraining Language Models"),
    ]
    paths = []
    for filename, title in titles:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", size=16)
        pdf.cell(text=title)
        pdf.ln(12)
        pdf.set_font("Helvetica", size=12)
        pdf.multi_cell(w=0, text=f"Content for {title}. This covers key NLP concepts.")
        # Add a few more pages
        for i in range(3):
            pdf.add_page()
            pdf.set_font("Helvetica", size=12)
            pdf.multi_cell(w=0, text=f"Page {i+2} content for {title}.")
        path = tmp_path / filename
        pdf.output(str(path))
        paths.append(str(path))
    return paths


@pytest.fixture
def temp_chroma_dir(tmp_path):
    return str(tmp_path / "test_chroma_db")
