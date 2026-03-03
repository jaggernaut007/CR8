# PDF Builder

**File**: `backend/services/pdf_builder.py`

Generates professional A4 PDF learning guides using `fpdf2`. Each PDF is a multi-chapter document with one chapter per topic/module, rendered in the CR8 "Midnight Teal" design language.

## Public API

```python
def build_pdf(
    title: str,           # Document title (shown on cover)
    topics: list[dict],   # [{"name": "...", "description": "..."}]
    modules_md: list[str], # Markdown content for each topic
    output_path: str,     # Output file path
) -> None
```

## Design System

### Color Palette

| Token | Hex | RGB | Usage |
|-------|-----|-----|-------|
| Deep Navy | `#0D1B2A` | (13, 27, 42) | Cover background, chapter titles |
| Teal | `#1B998B` | (27, 153, 139) | Accent lines, highlights |
| Warm Gold | `#F4B942` | (244, 185, 66) | Callout markers |
| Off White | `#F7F7F2` | (247, 247, 242) | Light backgrounds |
| Charcoal | `#2D3436` | (45, 52, 54) | Body text |
| Slate Gray | `#636E72` | (99, 110, 114) | Captions, footers |

### Fonts

| Element | Font | Notes |
|---------|------|-------|
| Headings | Times (serif) | Matches Georgia in PPT |
| Body | Helvetica (sans) | Matches Calibri in PPT |

### Page Settings

- **Page size**: A4 (210 x 297 mm)
- **Margins**: 25mm left/right, 20mm top/bottom
- **Library**: fpdf2

## Page Structure

1. **Cover Page** -- Full dark navy background, Times-Bold 30pt white title, teal accent lines, "Market-Enriched Learning Guide" subtitle in teal, generation date, topic count, "Powered by CR8" footer
2. **Table of Contents** -- Times-Bold 22pt navy heading, teal-numbered topic entries
3. **Chapters** (one per topic) -- Teal left accent bar, chapter number in teal, Times-Bold 20pt navy title, teal underline, optional slate gray italic description, markdown content rendering

## Rendering Capabilities

### LaTeX Math Rendering

- **Inline math**: `\( expr \)` -- rendered as PNG images via matplotlib, embedded inline at cursor position
- **Display math**: `\[ expr \]` -- rendered as centered equation images (14pt, 200dpi)
- **Fallback**: If matplotlib fails, LaTeX is converted to readable ASCII using `_LATEX_CMD_MAP` (e.g., `\alpha` -> "alpha", `\frac{a}{b}` -> "a/b")
- **Implementation**: `_render_latex_to_png()`, `_embed_latex_image()`, `_render_text_with_latex()`, `_render_display_math()`

### Rich Text Rendering

- **Bold**: `**text**` rendered as Helvetica-Bold inline
- **Italic**: `*text*` rendered as Helvetica-Italic inline
- **Mixed**: Handles interleaved bold/italic/plain text via `pdf.write()` calls
- **Markdown links**: `[text](url)` flattened to "text (url)"
- **Implementation**: `_render_rich_text()`

### Code Block Rendering

- Triple-backtick fenced code blocks detected during line processing
- Rendered in Courier 8pt on a light gray background (`#F0F0EB`)
- Auto page break if block doesn't fit
- **Implementation**: `_render_code_block()`

### Markdown Line Rendering (`_render_markdown_line()`)

| Element | Rendering |
|---------|-----------|
| `# H1` | Helvetica-Bold 14pt, navy, teal underline |
| `## H2` | Helvetica-Bold 13pt, navy, teal underline |
| `### H3` | Helvetica-Bold 11pt, teal |
| `#### H4+` | Helvetica-Bold 10pt, teal |
| `- bullet` | Teal dash marker + rich text body |
| `1. numbered` | Teal bold number + rich text body |
| `> blockquote` | Gold left accent bar, Helvetica-Italic 9pt slate gray |
| `---` / `***` | Teal horizontal rule |
| Display math | Centered matplotlib equation image |
| Inline HTML | Stripped (tags removed, content kept) |
| Inline code | Backticks stripped, content rendered as plain text |

## Unicode Handling

GPT models frequently emit Unicode characters that Helvetica (latin-1) cannot render. The `_sanitize()` function replaces 17+ Unicode characters:

- **Smart quotes**: right/left single and double quotes to ASCII equivalents
- **Dashes**: en dash, em dash, non-breaking hyphen to `-`/`--`
- **Bullets**: `*` to `-`, `>` to `>`
- **Zero-width characters**: ZWS, ZWNJ, ZWJ, BOM removed
- **Final fallback**: `encode("latin-1", errors="replace")` for any remaining characters
