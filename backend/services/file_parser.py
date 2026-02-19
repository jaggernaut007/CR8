import os
import pymupdf


def extract_text(file_path: str) -> list[dict]:
    """Extract text from a PDF or PPTX file.

    Returns a list of dicts: [{"text": "...", "source": "filename.pdf", "page": 1}, ...]
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        return _extract_pdf(file_path)
    elif ext == ".pptx":
        return _extract_pptx(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")


def _extract_pdf(file_path: str) -> list[dict]:
    source = os.path.basename(file_path)
    pages = []
    with pymupdf.open(file_path) as doc:
        for i, page in enumerate(doc):
            text = page.get_text()
            pages.append({"text": text, "source": source, "page": i + 1})
    return pages


def _extract_pptx(file_path: str) -> list[dict]:
    from pptx import Presentation

    source = os.path.basename(file_path)
    prs = Presentation(file_path)
    pages = []
    for i, slide in enumerate(prs.slides):
        texts = []
        for shape in slide.shapes:
            if shape.has_text_frame:
                texts.append(shape.text_frame.text)
        pages.append({"text": "\n".join(texts), "source": source, "page": i + 1})
    return pages
