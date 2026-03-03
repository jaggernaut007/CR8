# File Parser

**File**: `backend/services/file_parser.py`

Extracts text from curriculum files. Supports PDF (via PyMuPDF) and PowerPoint (via python-pptx).

## Usage

```python
from backend.services.file_parser import extract_text

pages = extract_text("lecture.pdf")
# Returns: [
#   {"text": "Lecture 1: Introduction...", "source": "lecture.pdf", "page": 1},
#   {"text": "Word embeddings are...",    "source": "lecture.pdf", "page": 2},
#   ...
# ]
```

## Function Signature

```python
def extract_text(file_path: str) -> list[dict]
```

Routes to the PDF or PPTX extractor based on file extension.

Each returned dict contains:

| Field | Type | Description |
|-------|------|-------------|
| `text` | `str` | Extracted text content for one page/slide |
| `source` | `str` | Original file path |
| `page` | `int` | Page or slide number (1-indexed) |

## Supported Formats

| Format | Extension | Library |
|--------|-----------|---------|
| PDF | `.pdf` | PyMuPDF (fitz) |
| PowerPoint | `.pptx` | python-pptx |
