# Research: fpdf2 PDF Generation

**Date researched:** 2026-03-09
**Library version:** >=2.8 (latest: 2026-02-28 release)
**Researched by:** Research Assistant Agent
**Status:** Current

---

## Question Being Answered

How do we use fpdf2 for multi-column PDF layout, font management, image embedding, and content formatting in CR8's PDF builder service?

## Sources Consulted

| Source | URL | Date accessed |
|--------|-----|---------------|
| Official fpdf2 Docs | https://py-pdf.github.io/fpdf2/ | 2026-03-09 |
| API Reference | https://py-pdf.github.io/fpdf2/fpdf/fpdf.html | 2026-03-09 |
| Unicode & Fonts | https://py-pdf.github.io/fpdf2/Unicode.html | 2026-03-09 |
| Text Methods | https://py-pdf.github.io/fpdf2/Text.html | 2026-03-09 |
| Image Embedding | https://py-pdf.github.io/fpdf2/Images.html | 2026-03-09 |
| Tables | https://py-pdf.github.io/fpdf2/Tables.html | 2026-03-09 |
| Metadata | https://py-pdf.github.io/fpdf2/Metadata.html | 2026-03-09 |
| Snyk Package Health | https://snyk.io/advisor/python/fpdf2 | 2026-03-09 |

## What We Found

### The Correct Approach

```python
from fpdf import FPDF
from io import BytesIO

class LearningGuidePDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 12)
        self.cell(0, 10, "CR8 Learning Guide", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

pdf = LearningGuidePDF(orientation="P", unit="mm", format="A4")
pdf.set_auto_page_break(auto=True, margin=15)
pdf.alias_nb_pages()
pdf.add_page()
```

### Key API Methods / Concepts

| Method / Concept | Purpose | Notes / Gotchas |
|-----------------|---------|----------------|
| `FPDF(orientation, unit, format)` | Initialize PDF | `"P"` portrait, `"mm"` millimeters, `"A4"` standard |
| `set_margins(left, top, right)` | Set page margins | Call before `add_page()` |
| `set_auto_page_break(auto, margin)` | Auto page break | `margin` = bottom margin before break |
| `set_font(family, style, size)` | Set current font | Built-in: Helvetica, Times, Courier (Latin-1 only) |
| `add_font(family, style, fname)` | Add TTF font | Required for Unicode support |
| `cell(w, h, text, ...)` | Single-line fixed-width cell | Use for labels, headers |
| `multi_cell(w, h, text, ...)` | Multi-line paragraph | Auto-wraps; use for body text |
| `write(h, text)` | Inline flowing text | Best for mixed bold/italic within a line |
| `image(name_or_io, x, y, w, h)` | Embed image | Accepts `BytesIO` for in-memory streams |
| `ln(h)` | Line break | Height in current unit (mm) |
| `set_text_color(r, g, b)` | Text color | Applies to subsequent text |
| `set_fill_color(r, g, b)` | Background fill | Used with `fill=True` in cell/multi_cell |

### Text Method Comparison

| Method | Multi-line | Inline | Auto-wrap | Best For |
|--------|-----------|--------|-----------|----------|
| `cell()` | No | No | No | Headers, labels, table cells |
| `multi_cell()` | Yes | No | Yes | Paragraphs, body text |
| `write()` | Yes | Yes | Yes | Mixed formatting within a line |

### Image Embedding (In-Memory)

```python
# CR8 pattern: render LaTeX via matplotlib, embed as PNG
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(4, 1))
ax.text(0.5, 0.5, r"$E = mc^2$", fontsize=20, ha="center")
ax.axis("off")

buf = BytesIO()
fig.savefig(buf, format="png", bbox_inches="tight", dpi=150)
buf.seek(0)
plt.close(fig)

pdf.image(buf, x=pdf.get_x(), y=pdf.get_y(), w=80)
```

### Table Generation (Context Manager API)

```python
with pdf.table(col_widths=[40, 80, 30]) as table:
    header = table.row()
    header.cell("Topic")
    header.cell("Description")
    header.cell("Score")
    for item in data:
        row = table.row()
        row.cell(item["topic"])
        row.cell(item["description"])
        row.cell(str(item["score"]))
```

### Configuration Required

```toml
# pyproject.toml
[project]
dependencies = ["fpdf2>=2.8"]
```

No environment variables needed — fpdf2 is a pure Python library.

## What We Ruled Out (and Why)

| Approach | Why Rejected |
|----------|-------------|
| ReportLab | Commercial license for advanced features; fpdf2 is MIT |
| WeasyPrint | Heavy dependency (Cairo, Pango); overkill for structured PDFs |
| PyPDF2/PyMuPDF | Read/merge PDFs, not generate from scratch |
| HTML → PDF (wkhtmltopdf) | External binary dependency; hard to style precisely |

## Known Gotchas / Edge Cases

1. **Built-in fonts only support Latin-1** — CR8's `_sanitize()` converts Unicode quotes/dashes to ASCII. For full Unicode, add a TTF font with `add_font()`.
2. **No built-in multi-column text flow** — must be implemented manually by tracking x/y positions.
3. **No markdown parsing** — CR8 parses markdown manually into cell/multi_cell calls.
4. **LaTeX requires matplotlib** — render to PNG via matplotlib, then embed as image.
5. **`multi_cell()` advances y position** — calling it resets x to left margin. Use `new_x` and `new_y` params (v2.7+) to control flow.
6. **PDF metadata** — `set_title()`, `set_author()`, `set_subject()` exist but CR8 doesn't use them yet. Consider adding for accessibility.

## Security Assessment

| Check | Result | Notes |
|-------|--------|-------|
| Open CVEs (critical/high) | None | Clean as of 2026-03-09 |
| License | MIT (LGPL for original FPDF) | fpdf2 fork is MIT — fully compatible |
| Last release | 2026-02-28 | Active; py-pdf org maintains |
| Maintainer count | 5+ | py-pdf GitHub org |
| Transitive dependencies | Minimal (Pillow optional) | Pure Python core |
| Known security incidents | None | No supply chain issues |

### Content Security

- CR8's `_sanitize()` correctly strips/converts problematic characters before embedding
- `BytesIO` used for image embedding avoids path traversal risk
- No user-controlled file paths in PDF generation

**Verdict:** SAFE to use. Well-maintained, MIT license, no CVEs, minimal dependencies.

## Decision Made

Based on this research, we will:
> Continue using fpdf2 >=2.8 for PDF generation. Current implementation in `pdf_builder.py` follows best practices. Consider adding PDF metadata (`set_title`, `set_author`) for accessibility in a future pass. If Unicode curriculum content becomes common, add a TTF font instead of relying on `_sanitize()`.

## Files This Affects

- `backend/services/pdf_builder.py` — FPDF subclass, layout, text rendering, image embedding
- `pyproject.toml` — fpdf2 version pin

---
*If this research is more than 6 months old or the library has had a major version bump, re-verify before implementing.*
