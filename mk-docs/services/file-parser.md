# File Parser

**File**: `backend/services/file_parser.py`

Extracts text and exports slide images from curriculum files. Supports PDF (via PyMuPDF) and PowerPoint (via python-pptx / LibreOffice CLI).

## Text Extraction

### Usage

```python
from backend.services.file_parser import extract_text

pages = extract_text("lecture.pdf")
# Returns: [
#   {"text": "Lecture 1: Introduction...", "source": "lecture.pdf", "page": 1},
#   {"text": "Word embeddings are...",    "source": "lecture.pdf", "page": 2},
#   ...
# ]
```

### Function Signature

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

### Supported Formats

| Format | Extension | Library |
|--------|-----------|---------|
| PDF | `.pdf` | PyMuPDF (fitz) |
| PowerPoint | `.pptx` | python-pptx |

---

## Slide Image Export

Used by the Kokoro video pipeline to produce slide PNGs before video composition.

### Usage

```python
from backend.services.file_parser import export_slides_as_images

image_paths = export_slides_as_images(
    file_path="lecture.pdf",
    output_dir="outputs/slides/",
)
# Returns: ["outputs/slides/slide_01.png", "outputs/slides/slide_02.png", ...]
```

### Function Signature

```python
def export_slides_as_images(
    file_path: str,
    output_dir: str,
    dpi: int = 150,
) -> list[str]
```

**Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `file_path` | `str` | — | Path to the source PDF or PPTX file |
| `output_dir` | `str` | — | Directory where PNG files will be written |
| `dpi` | `int` | `150` | Render resolution for PDF pages (higher = larger file, sharper image) |

**Returns**: Ordered list of absolute paths to the exported PNG files (one per slide/page).

### Export Backends

| Source format | Export method | System requirement |
|--------------|--------------|-------------------|
| PDF | PyMuPDF `page.get_pixmap()` | None (pure Python) |
| PPTX | LibreOffice CLI → intermediate PDF → `pdftoppm` | `libreoffice`, `poppler-utils` |

### Security Notes

- Input path is validated to prevent path traversal before any file operations
- PPTX export uses a `tempfile.TemporaryDirectory()` context manager for automatic cleanup of intermediate files
- LibreOffice is invoked via `subprocess.run()` with an explicit argument list and a timeout (no shell=True)

!!! warning "System dependencies for PPTX export"
    PPTX slide export requires `libreoffice` and `poppler-utils` (for `pdftoppm`) to be installed. These are included in the project `Dockerfile`. For local development on macOS, install with `brew install libreoffice poppler`.

### Decorated for tracing

`export_slides_as_images` is decorated with `@traceable` for LangSmith observability. Every slide export call appears as a named span in LangSmith traces when `LANGCHAIN_TRACING_V2=true`.
