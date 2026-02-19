from backend.services.file_parser import extract_text


def test_extract_text_from_pdf(single_slide_pdf):
    pages = extract_text(single_slide_pdf)

    assert len(pages) > 0
    assert all("text" in p and "source" in p and "page" in p for p in pages)

    full_text = " ".join(p["text"] for p in pages).lower()
    # CS224N Lecture 1 covers word vectors — should contain these terms
    assert "word" in full_text
    assert pages[0]["source"] == "01_Word_Vectors_I.pdf"
    assert pages[0]["page"] == 1


def test_extract_text_returns_nonempty_pages(single_slide_pdf):
    pages = extract_text(single_slide_pdf)
    nonempty = [p for p in pages if p["text"].strip()]
    # At least some pages should have real text
    assert len(nonempty) >= 3


def test_extract_text_multiple_files(three_slide_pdfs):
    for path in three_slide_pdfs:
        pages = extract_text(path)
        assert len(pages) > 0
