"""PDF learning guide builder using fpdf2.

Generates a professional A4 PDF with the CR8 "Midnight Teal" design language:
Times (serif) for headings + Helvetica (sans) for body, matching the
Georgia + Calibri pairing in the PPT builder. Teal accent lines, navy
chapter titles, gold callouts, and CR8 branding throughout.

LaTeX math expressions are rendered as images via matplotlib and embedded
inline.  Reference: https://py-pdf.github.io/fpdf2/Maths.html

Design reference: Docs/CR8_Course_PPT_Template_Recommendation.md
"""

import logging
import os
import re
import struct
from datetime import datetime
from io import BytesIO

import matplotlib
matplotlib.use("Agg")
from matplotlib.figure import Figure

from fpdf import FPDF

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# "Midnight Teal" palette — RGB tuples for fpdf2
# ---------------------------------------------------------------------------
_DEEP_NAVY = (13, 27, 42)        # #0D1B2A — cover bg, chapter titles
_TEAL = (27, 153, 139)           # #1B998B — accent lines, highlights
_WARM_GOLD = (244, 185, 66)      # #F4B942 — callout markers
_OFF_WHITE = (247, 247, 242)     # #F7F7F2 — light backgrounds
_CHARCOAL = (45, 52, 54)         # #2D3436 — body text
_SLATE_GRAY = (99, 110, 114)     # #636E72 — captions, footers
_WHITE = (255, 255, 255)

# Page layout (mm)
_PAGE_W = 210   # A4 width
_PAGE_H = 297   # A4 height
_MARGIN_L = 25
_MARGIN_R = 25
_CONTENT_W = _PAGE_W - _MARGIN_L - _MARGIN_R

# Unicode chars that GPT likes to use but Helvetica (latin-1) can't render
_UNICODE_REPLACEMENTS = {
    "\u2018": "'",   # left single quote
    "\u2019": "'",   # right single quote
    "\u201c": '"',   # left double quote
    "\u201d": '"',   # right double quote
    "\u2013": "-",   # en dash
    "\u2014": "--",  # em dash
    "\u2026": "...", # ellipsis
    "\u2022": "-",   # bullet
    "\u2023": ">",   # triangle bullet
    "\u2032": "'",   # prime
    "\u2033": '"',   # double prime
    "\u00a0": " ",   # non-breaking space
    "\u2011": "-",   # non-breaking hyphen
    "\u2010": "-",   # hyphen
    "\u2212": "-",   # minus sign
    "\u200b": "",    # zero-width space
    "\u200c": "",    # zero-width non-joiner
    "\u200d": "",    # zero-width joiner
    "\ufeff": "",    # BOM
}


def _sanitize(text: str) -> str:
    """Replace Unicode chars that Helvetica can't render."""
    for char, replacement in _UNICODE_REPLACEMENTS.items():
        text = text.replace(char, replacement)
    # Catch any remaining non-latin-1 chars
    return text.encode("latin-1", errors="replace").decode("latin-1")


# ---------------------------------------------------------------------------
# LaTeX rendering — matplotlib images + text fallback
# ---------------------------------------------------------------------------

_INLINE_LATEX_RE = re.compile(r"\\\((.+?)\\\)")
_DISPLAY_LATEX_RE = re.compile(r"^\\\[(.+)\\\]$")

# Fallback: LaTeX command → readable ASCII (used when matplotlib fails)
_LATEX_CMD_MAP = {
    "\\mid": "|",
    "\\vert": "|",
    "\\cdot": "*",
    "\\times": "x",
    "\\leq": "<=",
    "\\geq": ">=",
    "\\neq": "!=",
    "\\approx": "~=",
    "\\infty": "inf",
    "\\rightarrow": "->",
    "\\leftarrow": "<-",
    "\\Rightarrow": "=>",
    "\\sum": "sum",
    "\\prod": "prod",
    "\\log": "log",
    "\\exp": "exp",
    "\\nabla": "grad",
    "\\partial": "d",
    "\\alpha": "alpha",
    "\\beta": "beta",
    "\\gamma": "gamma",
    "\\delta": "delta",
    "\\epsilon": "epsilon",
    "\\theta": "theta",
    "\\lambda": "lambda",
    "\\sigma": "sigma",
    "\\pi": "pi",
    "\\omega": "omega",
    "\\quad": " ",
    "\\qquad": "  ",
    "\\,": " ",
    "\\;": " ",
    "\\!": "",
    "\\ ": " ",
}


def _strip_latex_expr(expr: str) -> str:
    """Convert a single LaTeX math expression to readable ASCII (fallback)."""
    text = expr
    # \text{...}, \mathbf{...}, etc. → content only
    text = re.sub(
        r"\\(?:text|mathbf|mathrm|textbf|textit|mathbb|mathcal|operatorname)"
        r"\{([^}]*)\}",
        r"\1", text,
    )
    text = re.sub(r"\\frac\{([^}]*)\}\{([^}]*)\}", r"\1/\2", text)
    text = re.sub(r"\\sqrt\{([^}]*)\}", r"sqrt(\1)", text)
    text = text.replace("^\\top", "^T")
    text = text.replace("\\top", "T")
    for cmd, repl in _LATEX_CMD_MAP.items():
        text = text.replace(cmd, repl)
    # Remaining \command → remove
    text = re.sub(r"\\[a-zA-Z]+", "", text)
    # Superscript/subscript braces: ^{X} → ^X, _{X} → _X
    text = re.sub(r"([_^])\{([^}]*)\}", r"\1\2", text)
    text = re.sub(r"  +", " ", text)
    return text.strip()


def _strip_latex(text: str) -> str:
    """Strip all LaTeX notation from a text string (fallback converter)."""
    text = _INLINE_LATEX_RE.sub(lambda m: _strip_latex_expr(m.group(1)), text)
    text = _DISPLAY_LATEX_RE.sub(lambda m: _strip_latex_expr(m.group(1)), text)
    text = re.sub(r"\$\$(.+?)\$\$", lambda m: _strip_latex_expr(m.group(1)), text)
    return text


def _render_latex_to_png(
    expr: str, fontsize: int = 11, dpi: int = 150,
) -> BytesIO | None:
    """Render a LaTeX expression to a PNG buffer using matplotlib.

    Returns BytesIO on success, None if rendering fails.
    Reference: https://py-pdf.github.io/fpdf2/Maths.html
    """
    try:
        fig = Figure(figsize=(0.01, 0.01), dpi=dpi)
        fig.text(
            0.5, 0.5, f"${expr}$",
            fontsize=fontsize, ha="center", va="center",
            fontfamily="serif", color="#2D3436",
        )
        buf = BytesIO()
        fig.savefig(
            buf, format="png", dpi=dpi, bbox_inches="tight",
            pad_inches=0.02, facecolor="white", edgecolor="none",
        )
        buf.seek(0)
        return buf
    except Exception:
        return None


def _png_dimensions(buf: BytesIO) -> tuple[int, int]:
    """Read (width, height) in pixels from a PNG IHDR chunk."""
    pos = buf.tell()
    buf.seek(16)  # 8-byte signature + 4-byte length + 4-byte "IHDR"
    w = struct.unpack(">I", buf.read(4))[0]
    h = struct.unpack(">I", buf.read(4))[0]
    buf.seek(pos)
    return w, h


def _embed_latex_image(pdf: FPDF, buf: BytesIO, line_h: float = 6, dpi: int = 150):
    """Embed a rendered LaTeX PNG inline at the current cursor position."""
    w_px, h_px = _png_dimensions(buf)
    target_h = line_h * 0.85
    target_w = target_h * (w_px / h_px)

    x, y = pdf.get_x(), pdf.get_y()

    # Wrap to next line if image won't fit
    right_edge = _PAGE_W - _MARGIN_R
    if x + target_w > right_edge:
        pdf.ln(line_h)
        x = _MARGIN_L
        y = pdf.get_y()

    pdf.image(buf, x=x, y=y, w=target_w, h=target_h)
    pdf.set_xy(x + target_w, y)


def _render_text_with_latex(pdf: FPDF, text: str, line_h: float = 6):
    """Render text with inline LaTeX expressions as matplotlib images.

    Splits the text on ``\\( ... \\)`` patterns.  Text segments are rendered
    with ``pdf.write()``; LaTeX segments are rendered as inline PNG images
    via matplotlib.  Falls back to ASCII text conversion if rendering fails.
    """
    parts = _INLINE_LATEX_RE.split(text)

    for i, part in enumerate(parts):
        if i % 2 == 0:
            # Text segment
            if part:
                pdf.write(line_h, _sanitize(part))
        else:
            # LaTeX segment — try matplotlib rendering
            buf = _render_latex_to_png(part)
            if buf is not None:
                _embed_latex_image(pdf, buf, line_h)
            else:
                # Fallback: render as ASCII text
                pdf.write(line_h, _sanitize(_strip_latex_expr(part)))


def _render_display_math(pdf: FPDF, expr: str):
    """Render display math ``\\[ ... \\]`` as a centered equation image."""
    buf = _render_latex_to_png(expr, fontsize=14, dpi=200)
    if buf is not None:
        pdf.ln(4)
        w_px, h_px = _png_dimensions(buf)
        target_h = 10.0
        target_w = target_h * (w_px / h_px)
        if target_w > _CONTENT_W:
            target_w = _CONTENT_W
            target_h = target_w * (h_px / w_px)
        x_center = _MARGIN_L + (_CONTENT_W - target_w) / 2
        pdf.image(buf, x=x_center, y=pdf.get_y(), w=target_w, h=target_h)
        pdf.set_y(pdf.get_y() + target_h + 2)
        pdf.ln(4)
    else:
        pdf.set_font("Helvetica", "I", 10)
        pdf.set_text_color(*_CHARCOAL)
        fallback = _sanitize(_strip_latex_expr(expr))
        pdf.multi_cell(0, 6, fallback, align="C")
        pdf.ln(2)


# ---------------------------------------------------------------------------
# Custom PDF class
# ---------------------------------------------------------------------------

class _LearningGuidePDF(FPDF):
    """Custom PDF with CR8 Midnight Teal header/footer."""

    _is_cover = True   # suppress header/footer on cover page
    _doc_title = "Market-Enriched Learning Guide"

    def header(self):
        if self._is_cover:
            return
        # Teal accent bar across top (1.5mm tall)
        self.set_fill_color(*_TEAL)
        self.rect(0, 0, _PAGE_W, 1.5, "F")

        # Right-aligned doc title in slate gray italic
        self.set_y(4)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*_SLATE_GRAY)
        self.cell(0, 5, self._doc_title, align="R", new_x="LMARGIN", new_y="NEXT")
        self.ln(4)

    def footer(self):
        if self._is_cover:
            return
        self.set_y(-15)
        # Thin teal line above footer
        self.set_draw_color(*_TEAL)
        self.set_line_width(0.3)
        self.line(_MARGIN_L, self.get_y(), _PAGE_W - _MARGIN_R, self.get_y())

        self.set_y(-12)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(*_SLATE_GRAY)
        self.cell(0, 5, f"Powered by CR8  |  Page {self.page_no()}", align="C")


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------

def _draw_teal_accent_line(pdf, x, y, width, thickness=0.8):
    """Draw a horizontal teal accent line."""
    pdf.set_fill_color(*_TEAL)
    pdf.rect(x, y, width, thickness, "F")


def _draw_gold_accent_line(pdf, x, y, width, thickness=0.8):
    """Draw a horizontal warm gold accent line."""
    pdf.set_fill_color(*_WARM_GOLD)
    pdf.rect(x, y, width, thickness, "F")


def _draw_teal_left_bar(pdf, x, y, height, width=1.2):
    """Draw a vertical teal accent bar (left border for content blocks)."""
    pdf.set_fill_color(*_TEAL)
    pdf.rect(x, y, width, height, "F")


# ---------------------------------------------------------------------------
# Rich text renderer (handles **bold**, *italic*, and inline LaTeX)
# ---------------------------------------------------------------------------

def _render_rich_text(pdf: FPDF, text: str, base_size: int = 10):
    """Render text with inline **bold**, *italic*, and LaTeX formatting.

    If the text contains ``\\( ... \\)`` LaTeX, it delegates to
    ``_render_text_with_latex`` which embeds matplotlib-rendered images.
    Otherwise it handles bold/italic markdown formatting.
    """
    # Flatten markdown links first
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", text)

    # Check for inline LaTeX
    if _INLINE_LATEX_RE.search(text):
        _render_text_with_latex(pdf, text)
        pdf.ln()
        return

    # No LaTeX — handle bold/italic
    parts = re.split(r"(\*\*[^*]+\*\*|\*[^*]+\*)", text)
    if len(parts) == 1:
        # No inline formatting — plain text
        pdf.multi_cell(0, 6, _sanitize(text))
        return

    # Use write() for inline mixed formatting
    for part in parts:
        if part.startswith("**") and part.endswith("**"):
            pdf.set_font("Helvetica", "B", base_size)
            pdf.write(6, _sanitize(part[2:-2]))
            pdf.set_font("Helvetica", "", base_size)
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            pdf.set_font("Helvetica", "I", base_size)
            pdf.write(6, _sanitize(part[1:-1]))
            pdf.set_font("Helvetica", "", base_size)
        else:
            pdf.write(6, _sanitize(part))
    pdf.ln()


# ---------------------------------------------------------------------------
# Code block renderer
# ---------------------------------------------------------------------------

_CODE_BG = (240, 240, 235)  # light gray for code blocks


def _render_code_block(pdf: FPDF, code_lines: list[str]):
    """Render a code block with Courier font and light gray background."""
    pdf.ln(2)
    x_start = _MARGIN_L + 4
    block_width = _CONTENT_W - 8

    # Estimate block height
    line_h = 5
    block_h = len(code_lines) * line_h + 4

    # Check if we need a page break
    if pdf.get_y() + block_h > _PAGE_H - 25:
        pdf.add_page()

    y_start = pdf.get_y()
    pdf.set_fill_color(*_CODE_BG)
    pdf.rect(x_start, y_start, block_width, block_h, "F")

    pdf.set_font("Courier", "", 8)
    pdf.set_text_color(*_CHARCOAL)
    pdf.set_y(y_start + 2)
    for code_line in code_lines:
        pdf.set_x(x_start + 3)
        pdf.cell(block_width - 6, line_h, _sanitize(code_line), new_x="LMARGIN", new_y="NEXT")

    pdf.set_y(y_start + block_h + 2)
    pdf.ln(2)


# ---------------------------------------------------------------------------
# Markdown line renderer
# ---------------------------------------------------------------------------

def _render_markdown_line(pdf: FPDF, line: str):
    """Render a single line of markdown to the PDF with Midnight Teal styling.

    Handles all standard markdown: headings (#–######), bullet and numbered
    lists, blockquotes, horizontal rules, inline HTML, inline code backticks,
    and inline LaTeX math via matplotlib images.
    """
    stripped = line.strip()

    # Pre-process: strip inline HTML tags
    if "<" in stripped and ">" in stripped:
        stripped = re.sub(r"<[^>]+>", "", stripped).strip()

    # Strip inline code backticks
    stripped = re.sub(r"`([^`]*)`", r"\1", stripped)

    if not stripped:
        pdf.ln(4)
        return

    # --- Horizontal rules (---, ***, ___) ---
    if re.match(r"^[-*_]{3,}\s*$", stripped):
        pdf.ln(3)
        _draw_teal_accent_line(pdf, _MARGIN_L + 20, pdf.get_y(), _CONTENT_W - 40, 0.4)
        pdf.ln(5)
        return

    # --- Display math: \[ ... \] → centered equation image ---
    display_match = _DISPLAY_LATEX_RE.match(stripped)
    if display_match:
        _render_display_math(pdf, display_match.group(1))
        return

    # --- Headings (deepest first; LaTeX stripped to text for headings) ---
    h4_match = re.match(r"^#{4,6}\s+(.*)", stripped)
    if h4_match:
        pdf.ln(4)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*_TEAL)
        heading = _sanitize(_strip_latex(h4_match.group(1)))
        pdf.cell(0, 6, heading, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
        return

    if stripped.startswith("### "):
        pdf.ln(5)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*_TEAL)
        heading = _sanitize(_strip_latex(stripped[4:]))
        pdf.cell(0, 7, heading, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
        return

    if stripped.startswith("## "):
        pdf.ln(6)
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(*_DEEP_NAVY)
        heading = _sanitize(_strip_latex(stripped[3:]))
        pdf.cell(0, 8, heading, new_x="LMARGIN", new_y="NEXT")
        # Teal accent line under heading
        _draw_teal_accent_line(pdf, _MARGIN_L, pdf.get_y(), 40)
        pdf.ln(3)
        return

    if stripped.startswith("# "):
        pdf.ln(6)
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(*_DEEP_NAVY)
        heading = _sanitize(_strip_latex(stripped[2:]))
        pdf.cell(0, 9, heading, new_x="LMARGIN", new_y="NEXT")
        _draw_teal_accent_line(pdf, _MARGIN_L, pdf.get_y(), 40)
        pdf.ln(3)
        return

    # --- Bullet points — teal dash with rich text ---
    if stripped.startswith("- ") or stripped.startswith("* "):
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(*_CHARCOAL)
        text = stripped[2:]
        # Teal bullet marker
        pdf.set_text_color(*_TEAL)
        pdf.cell(8)
        pdf.cell(4, 6, "-")
        pdf.set_text_color(*_CHARCOAL)
        pdf.set_font("Helvetica", "", 10)
        _render_rich_text(pdf, f" {text}", 10)
        pdf.ln(1)
        return

    # --- Numbered lists — teal number with rich text ---
    num_match = re.match(r"^(\d+)\.\s+(.*)", stripped)
    if num_match:
        num_label = num_match.group(1) + "."
        text = num_match.group(2)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*_TEAL)
        pdf.cell(8)
        pdf.cell(6, 6, num_label)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(*_CHARCOAL)
        _render_rich_text(pdf, f" {text}", 10)
        pdf.ln(1)
        return

    # --- Blockquotes / callouts — gold left bar, slate gray italic ---
    if stripped.startswith("> "):
        text = stripped[2:]
        text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
        bar_y = pdf.get_y()
        # Gold accent bar on the left
        pdf.set_fill_color(*_WARM_GOLD)
        pdf.rect(_MARGIN_L + 4, bar_y, 1.2, 6, "F")
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(*_SLATE_GRAY)
        pdf.cell(10)
        pdf.multi_cell(0, 6, _sanitize(_strip_latex(text)))
        pdf.ln(1)
        return

    # --- Regular paragraph text — charcoal body with rich text ---
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*_CHARCOAL)
    _render_rich_text(pdf, stripped, 10)
    pdf.ln(2)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_pdf(
    title: str,
    topics: list[dict],
    modules_md: list[str],
    output_path: str,
):
    """Build a CR8-branded PDF learning guide from topic list and markdown modules.

    Uses the "Midnight Teal" design system:
    - Times (serif) for cover title and chapter headings
    - Helvetica (sans) for body text
    - Teal accent lines, navy headings, CR8 branding

    The generated PDF includes a cover page, table of contents, and one
    chapter per topic with fully rendered markdown (headings, lists,
    code blocks, inline LaTeX via matplotlib).

    Args:
        title: Document title displayed on the cover page.
        topics: List of topic dicts (each must have a ``"name"`` key;
            optional ``"description"`` is shown beneath the chapter title).
        modules_md: Parallel list of markdown strings, one per topic.
        output_path: Filesystem path where the PDF will be written.
            Parent directories are created automatically.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    pdf = _LearningGuidePDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(_MARGIN_L, 20, _MARGIN_R)

    # --- Cover page (dark navy background) ---
    pdf._is_cover = True
    pdf.add_page()

    # Full-page navy background
    pdf.set_fill_color(*_DEEP_NAVY)
    pdf.rect(0, 0, _PAGE_W, _PAGE_H, "F")

    # Teal accent line near top
    _draw_teal_accent_line(pdf, 60, 65, 90, 1.0)

    # Main title — Times-Bold (serif), white, centered
    pdf.set_y(80)
    pdf.set_font("Times", "B", 30)
    pdf.set_text_color(*_WHITE)
    pdf.multi_cell(0, 14, _sanitize(title), align="C")

    # Teal accent line below title
    _draw_teal_accent_line(pdf, 60, pdf.get_y() + 5, 90, 1.0)

    # Subtitle — Helvetica, teal
    pdf.set_y(pdf.get_y() + 12)
    pdf.set_font("Helvetica", "", 14)
    pdf.set_text_color(*_TEAL)
    pdf.cell(0, 10, "Market-Enriched Learning Guide", align="C",
             new_x="LMARGIN", new_y="NEXT")

    # Metadata — slate gray
    pdf.ln(5)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(*_SLATE_GRAY)
    pdf.cell(0, 8, f"Generated: {datetime.now().strftime('%B %d, %Y')}",
             align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"{len(topics)} topics covered",
             align="C", new_x="LMARGIN", new_y="NEXT")

    # Gold accent line near bottom
    _draw_gold_accent_line(pdf, 70, 230, 70, 0.8)

    # Footer branding
    pdf.set_y(240)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(*_SLATE_GRAY)
    pdf.cell(0, 8, "Powered by CR8", align="C",
             new_x="LMARGIN", new_y="NEXT")

    # --- Table of Contents ---
    pdf._is_cover = False
    pdf.add_page()

    # TOC heading — Times-Bold (serif), navy
    pdf.set_font("Times", "B", 22)
    pdf.set_text_color(*_DEEP_NAVY)
    pdf.cell(0, 12, "Table of Contents", new_x="LMARGIN", new_y="NEXT")

    # Teal accent line under TOC heading
    _draw_teal_accent_line(pdf, _MARGIN_L, pdf.get_y() + 2, 50)
    pdf.ln(8)

    # Topic entries — charcoal, with teal numbering
    for i, topic in enumerate(topics):
        # Teal chapter number
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*_TEAL)
        num_text = f"{i + 1}."
        pdf.cell(12, 8, num_text)

        # Topic name in charcoal
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(*_CHARCOAL)
        pdf.cell(0, 8, _sanitize(topic["name"]),
                 new_x="LMARGIN", new_y="NEXT")

    # --- Chapters ---
    for i, (topic, module_md) in enumerate(zip(topics, modules_md)):
        pdf.add_page()

        # Teal left accent bar alongside chapter title
        bar_y = pdf.get_y()
        _draw_teal_left_bar(pdf, _MARGIN_L - 4, bar_y, 14)

        # Chapter number in teal
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(*_TEAL)
        pdf.cell(0, 6, f"Chapter {i + 1}", new_x="LMARGIN", new_y="NEXT")

        # Chapter title — Times-Bold (serif), navy
        pdf.set_font("Times", "B", 20)
        pdf.set_text_color(*_DEEP_NAVY)
        pdf.multi_cell(0, 10, _sanitize(topic["name"]))

        # Teal accent line under chapter title
        _draw_teal_accent_line(pdf, _MARGIN_L, pdf.get_y() + 1, 60)
        pdf.ln(4)

        # Topic description — slate gray italic
        if topic.get("description"):
            pdf.set_font("Helvetica", "I", 10)
            pdf.set_text_color(*_SLATE_GRAY)
            pdf.multi_cell(0, 6, _sanitize(topic["description"]))
            pdf.ln(4)

        # Render module content (with code block preprocessing)
        lines = module_md.split("\n")
        i_line = 0
        while i_line < len(lines):
            line = lines[i_line]
            # Detect triple-backtick code blocks
            if line.strip().startswith("```"):
                code_lines = []
                i_line += 1
                while i_line < len(lines) and not lines[i_line].strip().startswith("```"):
                    code_lines.append(lines[i_line])
                    i_line += 1
                i_line += 1  # skip closing ```
                if code_lines:
                    _render_code_block(pdf, code_lines)
            else:
                _render_markdown_line(pdf, line)
                i_line += 1

    pdf.output(output_path)
