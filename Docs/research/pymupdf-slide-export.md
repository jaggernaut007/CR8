# Research: PyMuPDF Slide Export

**Date researched:** 2026-03-03
**Library version:** pymupdf>=1.24
**Researched by:** Claude Agent (research-assistant)
**Status:** Current

---

## Question Being Answered

> How do we render PDF pages to PNG images using PyMuPDF v1.24+ for CR8's slide export?

## Sources Consulted

| Source | URL | Date accessed |
|--------|-----|---------------|
| PyMuPDF docs (Page) | https://pymupdf.readthedocs.io/en/latest/page.html | 2026-03-03 |
| PyMuPDF docs (Pixmap) | https://pymupdf.readthedocs.io/en/latest/pixmap.html | 2026-03-03 |

## What We Found

### The Correct Approach
```python
import pymupdf

with pymupdf.open(file_path) as doc:
    for i, page in enumerate(doc):
        pix = page.get_pixmap(dpi=150)  # ~1920×1080 for standard slides
        pix.save(f"slide_{i + 1:03d}.png")  # Auto-detects format from extension
```

### Key API Methods / Concepts
| Method / Concept | Purpose | Notes / Gotchas |
|-----------------|---------|----------------|
| `page.get_pixmap(dpi=150)` | Render page to in-memory image | `dpi` param added in v1.20+. 150 DPI ≈ 1920×1080. Baseline is 72 DPI. |
| `pix.save(path)` | Write pixmap to disk | Auto-detects format from extension (.png, .jpg). Unified API in v1.24+. |
| `pymupdf.open(path)` | Open PDF document | Use as context manager (`with`) for proper cleanup. |
| `alpha=False` | Disable transparency | Saves ~25% memory. Use when transparency not needed (slides). |

### DPI Reference
| DPI | Approx Resolution | Memory per Page | Use Case |
|-----|-------------------|----------------|----------|
| 72 | 612×792 | ~2 MB | Screen preview |
| 150 | 1275×1650 | ~8 MB | HD slides (our default) |
| 300 | 2550×3300 | ~32 MB | Print quality |

### Configuration Required
```bash
# Python (already a CR8 dependency)
pip install pymupdf>=1.24

# For PPTX support, LibreOffice converts to PDF first
apt-get install libreoffice  # or poppler-utils for pdftoppm
```

## What We Ruled Out (and Why)

| Approach | Why Rejected |
|----------|-------------|
| `Matrix(zoom, zoom)` approach | Pre-v1.20 pattern. `dpi` parameter is clearer and idiomatic for v1.24+. |
| `page.get_image()` | Retrieves embedded images, not renders the page. Wrong API for slide export. |
| Pillow for PNG encoding | Unnecessary — PyMuPDF's `pix.save()` handles all formats natively. |
| Loading all pixmaps into memory | OOM risk on large PDFs. Sequential processing is safer. |

## Known Gotchas / Edge Cases

- **PyMuPDF is NOT thread-safe at the document level** — Don't share a `doc` object across threads. Open a new document per thread if parallelizing.
- **Default colorspace is RGBA (4-channel)** — Use `alpha=False` to save 25% memory when transparency not needed.
- **Corrupted PDF pages** — `get_pixmap()` raises an exception. Consider wrapping in try/except for graceful degradation on large uploads.
- **PPTX requires two-step conversion** — LibreOffice CLI converts PPTX→PDF first, then PyMuPDF renders the PDF pages.
- **3-digit zero-padding** — `f"slide_{i+1:03d}.png"` ensures correct sort order up to 999 pages.

## Decision Made

> Use `page.get_pixmap(dpi=150)` with sequential page processing. For PPTX, convert to PDF via LibreOffice CLI first, then render.

## Files This Affects

- `backend/services/file_parser.py` — `export_slides_as_images()`, `_export_pdf_pages()`, `_export_pptx_pages()`
- `Dockerfile` — `poppler-utils` for PDF tools

---
*Re-verify if PyMuPDF releases v2.0 with breaking API changes.*
