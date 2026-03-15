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
    dpi: int = 144,
) -> list[str]
```

**Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `file_path` | `str` | — | Path to the source PDF or PPTX file |
| `output_dir` | `str` | — | Directory where PNG files will be written |
| `dpi` | `int` | `144` | Render resolution (144 DPI on a 13.333" × 7.5" widescreen slide produces 1920 × 1080 pixels) |

**Returns**: Sorted list of PNG file paths (`slide_001.png`, `slide_002.png`, ...).

**Raises**:

| Exception | Condition |
|-----------|-----------|
| `ValueError` | Unsupported file extension, or `output_dir` fails the path traversal check |
| `RuntimeError` | LibreOffice is not installed, or LibreOffice PPTX→PDF conversion exits non-zero |

### Export Backends

| Source format | Export method | System requirement |
|--------------|--------------|-------------------|
| PDF | PyMuPDF `page.get_pixmap()` | None (pure Python) |
| PPTX | LibreOffice CLI → intermediate PDF → PyMuPDF | `libreoffice` |

### Path Traversal Protection

`export_slides_as_images` calls `_validate_output_dir(output_dir)` before any file operations. The guard resolves `output_dir` with `os.path.realpath()` (which expands symlinks) and rejects any path that is not under the current working directory or the system temporary directory. Attempts to write to paths like `/etc/evil`, `../../../../etc/shadow`, or a symlink pointing outside allowed roots all raise `ValueError: Path traversal detected: <path>`.

```python
from backend.services.file_parser import _validate_output_dir

_validate_output_dir("/etc/evil")           # raises ValueError
_validate_output_dir("/tmp/safe/subdir")    # accepted
_validate_output_dir("outputs/slides")     # accepted (under cwd)
```

### Security Notes

- `_validate_output_dir` uses `os.path.realpath()` (not `abspath`) to resolve symlinks before the boundary check — symlink escape attempts are caught
- PPTX export uses a `tempfile.TemporaryDirectory()` context manager for automatic cleanup of intermediate files
- LibreOffice is invoked via `subprocess.run()` with an explicit argument list, a 60-second timeout, and `shell=False`

!!! warning "System dependencies for PPTX export"
    PPTX slide export requires `libreoffice` to be installed. It is included in `Dockerfile.gpu` and `Dockerfile.cpu-video`. The main pipeline `Dockerfile` does not include LibreOffice — slide export on the CPU pipeline container is intentionally deferred to the GPU or CPU-video remote worker. For local development on macOS: `brew install libreoffice`.

### Decorated for tracing

`export_slides_as_images` is decorated with `@traceable` for LangSmith observability. Every slide export call appears as a named span in LangSmith traces when `LANGCHAIN_TRACING_V2=true`.
