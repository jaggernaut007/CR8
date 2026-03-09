# Research: python-pptx PowerPoint Generation

**Date researched:** 2026-03-09
**Library version:** >=1.0 (latest: v1.0.2)
**Researched by:** Research Assistant Agent
**Status:** Current

---

## Question Being Answered

How do we use python-pptx for slide creation, shape positioning, text formatting, and slide notes (TTS scripts) in CR8's PPT builder service?

## Sources Consulted

| Source | URL | Date accessed |
|--------|-----|---------------|
| python-pptx Docs | https://python-pptx.readthedocs.io/ | 2026-03-09 |
| API Reference | https://python-pptx.readthedocs.io/en/latest/api/presentation.html | 2026-03-09 |
| Slide Layouts | https://python-pptx.readthedocs.io/en/latest/user/slides.html | 2026-03-09 |
| Text & Fonts | https://python-pptx.readthedocs.io/en/latest/user/text.html | 2026-03-09 |
| Shapes & Positioning | https://python-pptx.readthedocs.io/en/latest/user/autoshapes.html | 2026-03-09 |
| PyPI Package | https://pypi.org/project/python-pptx/ | 2026-03-09 |

## What We Found

### The Correct Approach

```python
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

prs = Presentation()
prs.slide_width = Inches(13.333)  # 16:9 widescreen
prs.slide_height = Inches(7.5)

# Use a blank layout
blank_layout = prs.slide_layouts[6]  # Index 6 = Blank
slide = prs.slides.add_slide(blank_layout)

# Add a text box with formatting
from pptx.util import Inches, Pt
txBox = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(8), Inches(1.5))
tf = txBox.text_frame
tf.word_wrap = True
p = tf.paragraphs[0]
p.text = "Lecture Title"
p.font.size = Pt(28)
p.font.bold = True
p.font.color.rgb = RGBColor(0x1A, 0x1A, 0x2E)
p.alignment = PP_ALIGN.LEFT

# Add slide notes (used for TTS scripts in CR8)
notes_slide = slide.notes_slide
notes_slide.notes_text_frame.text = "Welcome to today's lecture on transformers..."

prs.save("output.pptx")
```

### Key API Methods / Concepts

| Method / Concept | Purpose | Notes / Gotchas |
|-----------------|---------|----------------|
| `Presentation()` | Create new PPTX | Defaults to 4:3; set `slide_width`/`slide_height` for 16:9 |
| `prs.slide_layouts[N]` | Access slide layout | 0=Title, 1=Title+Content, 5=Blank, 6=Blank (varies by template) |
| `prs.slides.add_slide(layout)` | Add a slide | Returns Slide object |
| `slide.shapes.add_textbox(l, t, w, h)` | Add text box | Positioning in Inches/Pt/Emu |
| `slide.shapes.add_picture(path, l, t, w, h)` | Add image | Accepts file path or file-like object |
| `slide.shapes.add_table(rows, cols, l, t, w, h)` | Add table | Returns GraphicFrame with `.table` property |
| `slide.notes_slide.notes_text_frame` | Access slide notes | CR8 uses this for TTS narration scripts |
| `text_frame.paragraphs[0]` | First paragraph | Auto-created; add more with `text_frame.add_paragraph()` |
| `paragraph.add_run()` | Add text run | Runs allow mixed formatting within a paragraph |
| `run.font.size = Pt(N)` | Set font size | Use `Pt()` for points |
| `run.font.color.rgb = RGBColor(r, g, b)` | Set color | Hex values (0x00-0xFF) |

### Unit System

| Unit | Constructor | Use Case |
|------|------------|----------|
| `Inches(n)` | Physical inches | Most common; intuitive positioning |
| `Pt(n)` | Points (1/72 inch) | Font sizes |
| `Emu(n)` | English Metric Units | Precise positioning (914400 EMU = 1 inch) |
| `Cm(n)` | Centimeters | Alternative to inches |

### Text Formatting Hierarchy

```
Presentation
  └── Slide
        └── Shape (TextBox, Placeholder)
              └── TextFrame
                    ├── word_wrap = True
                    └── Paragraph (one or more)
                          ├── alignment = PP_ALIGN.LEFT
                          ├── space_before = Pt(6)
                          └── Run (one or more)
                                ├── text = "Hello"
                                ├── font.size = Pt(14)
                                ├── font.bold = True
                                └── font.color.rgb = RGBColor(...)
```

### Slide Notes for TTS (CR8 Pattern)

```python
# In ppt_builder.py — attach narration script to each slide
notes_slide = slide.notes_slide
tf = notes_slide.notes_text_frame
tf.text = ""  # Clear default
p = tf.paragraphs[0]
p.text = tts_script_for_this_slide

# Later, in video_builder.py — extract scripts
for slide in prs.slides:
    script = slide.notes_slide.notes_text_frame.text
    audio = tts_engine.synthesize(script)
```

### Configuration Required

```toml
# pyproject.toml
[project]
dependencies = ["python-pptx>=1.0"]
```

No environment variables needed — pure Python library.

## What We Ruled Out (and Why)

| Approach | Why Rejected |
|----------|-------------|
| python-docx | Wrong format (Word, not PowerPoint) |
| LibreOffice API (python-uno) | Complex setup, requires running LibreOffice instance |
| Google Slides API | Requires Google account, network dependency |
| Reveal.js (HTML slides) | Not PPTX format; can't be used with TTS pipeline |

## Known Gotchas / Edge Cases

1. **Slide layout indices vary by template** — Blank layout is typically index 5 or 6, but always verify with your template.
2. **No animation support** — python-pptx cannot add slide transitions or shape animations.
3. **No chart editing** — Can add charts but editing existing chart data is limited.
4. **Placeholder indices** — Placeholder shapes have fixed indices (0=title, 1=body). Using wrong index raises `KeyError`.
5. **Image sizing** — If you specify only width, height auto-scales. If both, aspect ratio may distort.
6. **Default font** — Without explicit font setting, uses Calibri (may not be available on all systems).
7. **Slide notes auto-creation** — Accessing `slide.notes_slide` creates the notes slide if it doesn't exist (side effect).

## Security Assessment

| Check | Result | Notes |
|-------|--------|-------|
| Open CVEs (critical/high) | None in python-pptx | Clean as of 2026-03-09 |
| License | MIT | Fully compatible |
| Last release | 2024-08 (v1.0.2) | Stable; single maintainer (Steve Canny) |
| Maintainer count | 1 (primary) | WARNING: single maintainer, but very stable API |
| Transitive dependencies | lxml, Pillow, XlsxWriter | lxml has historical XXE risk — mitigated in recent versions |
| Known security incidents | None | No supply chain issues |

### lxml XXE Risk (Transitive)

- python-pptx uses lxml for XML parsing
- lxml has had historical XXE (XML External Entity) vulnerabilities
- Modern lxml (>=4.9) disables external entity resolution by default
- CR8 generates PPTX from internal data (not user-uploaded PPTX), so risk is minimal

**Verdict:** SAFE to use. Stable API, MIT license, no direct CVEs. Single maintainer is a minor risk but the library is mature (v1.0+).

## Decision Made

Based on this research, we will:
> Continue using python-pptx >=1.0 for PowerPoint generation. Current implementation in `ppt_builder.py` correctly uses slide notes for TTS scripts, proper positioning with `Inches()`/`Pt()`, and text formatting hierarchy. No changes needed.

## Files This Affects

- `backend/services/ppt_builder.py` — Presentation creation, slide layouts, text/image placement, notes
- `backend/services/video_builder.py` — Reads slide notes for TTS scripts
- `backend/services/pdf_builder.py` — Uses PyMuPDF to export PPTX slides as images (related)
- `pyproject.toml` — python-pptx version pin

---
*If this research is more than 6 months old or the library has had a major version bump, re-verify before implementing.*
