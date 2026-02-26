"""PDF learning guide builder using fpdf2.

Generates a professional A4 PDF with the CR8 "Midnight Teal" design language:
Times (serif) for headings + Helvetica (sans) for body, matching the
Georgia + Calibri pairing in the PPT builder. Teal accent lines, navy
chapter titles, gold callouts, and CR8 branding throughout.

Design reference: Docs/CR8_Course_PPT_Template_Recommendation.md
"""

import os
import re
from datetime import datetime

from fpdf import FPDF

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
# Markdown line renderer
# ---------------------------------------------------------------------------

def _render_markdown_line(pdf: FPDF, line: str):
    """Render a single line of markdown to the PDF with Midnight Teal styling."""
    stripped = _sanitize(line.strip())
    if not stripped:
        pdf.ln(4)
        return

    # Section headings (##) — navy bold Helvetica with teal accent underline
    if stripped.startswith("## "):
        pdf.ln(6)
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(*_DEEP_NAVY)
        heading_text = stripped[3:]
        pdf.cell(0, 8, heading_text, new_x="LMARGIN", new_y="NEXT")
        # Teal accent line under heading
        _draw_teal_accent_line(pdf, _MARGIN_L, pdf.get_y(), 40)
        pdf.ln(3)
        return

    # Bullet points — teal dash
    if stripped.startswith("- ") or stripped.startswith("* "):
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(*_CHARCOAL)
        text = stripped[2:]
        text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", text)
        text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
        # Teal bullet marker
        pdf.set_text_color(*_TEAL)
        pdf.cell(8)
        pdf.cell(4, 6, "-")
        pdf.set_text_color(*_CHARCOAL)
        pdf.multi_cell(0, 6, f" {text}")
        pdf.ln(1)
        return

    # Regular paragraph text — charcoal body
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*_CHARCOAL)
    text = stripped
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    pdf.multi_cell(0, 6, text)
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

        # Render module content
        for line in module_md.split("\n"):
            _render_markdown_line(pdf, line)

    pdf.output(output_path)
