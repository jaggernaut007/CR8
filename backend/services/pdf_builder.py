import os
import re
from datetime import datetime

from fpdf import FPDF

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


class _LearningGuidePDF(FPDF):
    """Custom PDF class with header/footer."""

    def header(self):
        if self.page_no() > 1:
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(150, 150, 150)
            self.cell(0, 10, "Market-Enriched Learning Guide", align="R", new_x="LMARGIN", new_y="NEXT")
            self.ln(2)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")


def _render_markdown_line(pdf: FPDF, line: str):
    """Render a single line of markdown to the PDF."""
    stripped = _sanitize(line.strip())
    if not stripped:
        pdf.ln(4)
        return

    # Headings
    if stripped.startswith("## "):
        pdf.ln(6)
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(22, 33, 62)
        pdf.cell(0, 8, stripped[3:], new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
        return

    # Bullet points
    if stripped.startswith("- ") or stripped.startswith("* "):
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(51, 51, 51)
        text = stripped[2:]
        text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", text)
        text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
        pdf.cell(10)
        pdf.multi_cell(0, 6, f"-  {text}")
        pdf.ln(1)
        return

    # Regular paragraph text
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(51, 51, 51)
    text = stripped
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    pdf.multi_cell(0, 6, text)
    pdf.ln(2)


def build_pdf(
    title: str,
    topics: list[dict],
    modules_md: list[str],
    output_path: str,
):
    """Build a PDF from topic list and markdown modules."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    pdf = _LearningGuidePDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(25, 20, 25)

    # --- Cover page ---
    pdf.add_page()
    pdf.ln(80)
    pdf.set_font("Helvetica", "B", 28)
    pdf.set_text_color(26, 26, 46)
    pdf.multi_cell(0, 14, title, align="C")
    pdf.ln(10)
    pdf.set_font("Helvetica", "", 14)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 10, "Market-Enriched Learning Guide", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    pdf.cell(0, 10, f"Generated: {datetime.now().strftime('%B %d, %Y')}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 10, f"{len(topics)} topics covered", align="C", new_x="LMARGIN", new_y="NEXT")

    # --- Table of Contents ---
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(22, 33, 62)
    pdf.cell(0, 12, "Table of Contents", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(51, 51, 51)
    for i, topic in enumerate(topics):
        pdf.cell(0, 8, _sanitize(f"{i + 1}.  {topic['name']}"), new_x="LMARGIN", new_y="NEXT")

    # --- Chapters ---
    for i, (topic, module_md) in enumerate(zip(topics, modules_md)):
        pdf.add_page()

        # Chapter title
        pdf.set_font("Helvetica", "B", 20)
        pdf.set_text_color(26, 26, 46)
        pdf.multi_cell(0, 10, _sanitize(f"Chapter {i + 1}: {topic['name']}"))
        pdf.ln(2)

        # Topic description
        if topic.get("description"):
            pdf.set_font("Helvetica", "I", 10)
            pdf.set_text_color(100, 100, 100)
            pdf.multi_cell(0, 6, _sanitize(topic["description"]))
            pdf.ln(4)

        # Render module content
        for line in module_md.split("\n"):
            _render_markdown_line(pdf, line)

    pdf.output(output_path)
