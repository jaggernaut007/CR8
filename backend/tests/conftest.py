import pytest
from pathlib import Path

NLP_COURSE_DIR = Path(__file__).parent.parent.parent / "NLP_Course" / "CS224N_Downloads"


@pytest.fixture
def single_slide_pdf():
    path = NLP_COURSE_DIR / "Slides" / "01_Word_Vectors_I.pdf"
    assert path.exists(), f"Test data not found: {path}"
    return str(path)


@pytest.fixture
def three_slide_pdfs():
    files = [
        NLP_COURSE_DIR / "Slides" / "01_Word_Vectors_I.pdf",
        NLP_COURSE_DIR / "Slides" / "08_Transformers.pdf",
        NLP_COURSE_DIR / "Slides" / "09_Pretraining.pdf",
    ]
    for f in files:
        assert f.exists(), f"Test data not found: {f}"
    return [str(f) for f in files]


@pytest.fixture
def temp_chroma_dir(tmp_path):
    return str(tmp_path / "test_chroma_db")
