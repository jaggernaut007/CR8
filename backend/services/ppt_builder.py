"""Gap Analysis PowerPoint builder using python-pptx.

Generates a professional widescreen (16:9) presentation focused on
curriculum-industry gaps, using the CR8 "Midnight Teal" design language
with Georgia + Calibri typography and 8 slide master types aligned to
Mayer's multimedia learning principles.

Design reference: Docs/CR8_Course_PPT_Template_Recommendation.md
"""

import os
from datetime import datetime

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

# ---------------------------------------------------------------------------
# Design tokens — "Midnight Teal" CR8 palette
# ---------------------------------------------------------------------------
COLORS = {
    # Primary palette
    "deep_navy": RGBColor(0x0D, 0x1B, 0x2A),       # Dark slide backgrounds, title slides, section dividers
    "teal": RGBColor(0x1B, 0x99, 0x8B),             # Accent bars, icon circles, data highlights
    "warm_gold": RGBColor(0xF4, 0xB9, 0x42),        # Key stat callouts, attention markers, CTA
    "off_white": RGBColor(0xF7, 0xF7, 0xF2),        # Content slide backgrounds
    "charcoal": RGBColor(0x2D, 0x34, 0x36),         # Body text on light backgrounds
    "slate_gray": RGBColor(0x63, 0x6E, 0x72),       # Captions, source citations, secondary text
    "white": RGBColor(0xFF, 0xFF, 0xFF),             # Text on dark backgrounds
    # Tinted backgrounds
    "teal_tint": RGBColor(0xE6, 0xF5, 0xF3),        # ~8% teal opacity on white — stat cards
    "gold_tint": RGBColor(0xFE, 0xF6, 0xE2),        # ~8% gold opacity on white — highlight cards
    # Severity / Impact
    "severity_critical": RGBColor(0xE8, 0x3E, 0x3E),
    "severity_moderate": RGBColor(0xF5, 0xA6, 0x23),
    "severity_minor": RGBColor(0x4C, 0xAF, 0x50),
    "impact_high": RGBColor(0xE8, 0x3E, 0x3E),
    "impact_medium": RGBColor(0xF5, 0xA6, 0x23),
    "impact_low": RGBColor(0x4C, 0xAF, 0x50),
}

# Typography — Georgia (authority serif) for titles, Calibri (clean sans) for body
FONT_TITLE = "Georgia"
FONT_BODY = "Calibri"

# Slide dimensions (widescreen 16:9)
SLIDE_WIDTH = Inches(13.333)
SLIDE_HEIGHT = Inches(7.5)

# Layout constants
MARGIN = Inches(0.5)
CONTENT_GAP = Inches(0.3)
TITLE_ZONE_BOTTOM = Inches(1.5)     # Top ~20% of slide
FOOTER_ZONE_TOP = Inches(7.1)       # Bottom 5% of slide
FOOTER_HEIGHT = Inches(0.35)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _set_slide_bg(slide, color):
    """Set the background color of a slide."""
    background = slide.background
    fill = background.fill
    fill.solid()
    fill.fore_color.rgb = color


def _add_textbox(slide, left, top, width, height, text,
                 size=Pt(12), color=None, bold=False, italic=False,
                 alignment=PP_ALIGN.LEFT, font_family=None,
                 word_wrap=True, vertical_anchor=MSO_ANCHOR.TOP):
    """Add a text box with configured formatting."""
    if font_family is None:
        font_family = FONT_BODY
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = word_wrap
    tf.auto_size = None
    p = tf.paragraphs[0]
    p.text = str(text)
    p.font.size = size
    p.font.name = font_family
    p.font.bold = bold
    p.font.italic = italic
    p.alignment = alignment
    if color:
        p.font.color.rgb = color
    p.space_before = Pt(0)
    p.space_after = Pt(0)
    return txBox


def _add_rect(slide, left, top, width, height, fill_color=None, line_color=None):
    """Add a rectangle shape with optional fill and line."""
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, left, top, width, height
    )
    shape.line.fill.background()
    if fill_color:
        shape.fill.solid()
        shape.fill.fore_color.rgb = fill_color
    if line_color:
        shape.line.fill.solid()
        shape.line.color.rgb = line_color
        shape.line.width = Pt(1)
    else:
        shape.line.fill.background()
    return shape


def _add_rounded_rect(slide, left, top, width, height, fill_color):
    """Add a rounded rectangle shape."""
    shape = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_color
    shape.line.fill.background()
    return shape


def _add_badge(slide, left, top, width, height, text, fill_color):
    """Add a colored rounded-rectangle badge with white text."""
    shape = _add_rounded_rect(slide, left, top, width, height, fill_color)
    tf = shape.text_frame
    tf.word_wrap = False
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(10)
    p.font.bold = True
    p.font.color.rgb = COLORS["white"]
    p.font.name = FONT_BODY
    p.alignment = PP_ALIGN.CENTER
    tf.margin_left = Pt(0)
    tf.margin_right = Pt(0)
    tf.margin_top = Pt(0)
    tf.margin_bottom = Pt(0)
    return shape


def _add_oval(slide, left, top, width, height, fill_color):
    """Add an oval/circle shape."""
    shape = slide.shapes.add_shape(
        MSO_SHAPE.OVAL, left, top, width, height
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_color
    shape.line.fill.background()
    return shape


def _add_teal_accent_line(slide, left, top, width):
    """Add a teal accent horizontal line (4pt)."""
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, left, top, width, Pt(4)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = COLORS["teal"]
    shape.line.fill.background()
    return shape


def _add_separator_line(slide, left, top, width):
    """Add a thin horizontal separator line in slate gray."""
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, left, top, width, Pt(1)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = COLORS["slate_gray"]
    shape.line.fill.background()
    return shape


def _add_teal_accent_bar(slide, left, top, height):
    """Add a 4pt wide vertical teal accent bar (left border on text columns)."""
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, left, top, Pt(4), height
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = COLORS["teal"]
    shape.line.fill.background()
    return shape


def _add_footer(slide, university_name=""):
    """Add footer branding zone at the bottom of a content slide."""
    date_str = datetime.now().strftime("%B %d, %Y")
    parts = ["Powered by CR8"]
    if university_name:
        parts.append(university_name)
    parts.append(date_str)
    footer_text = "  |  ".join(parts)
    _add_textbox(slide, MARGIN, FOOTER_ZONE_TOP, Inches(12), FOOTER_HEIGHT,
                 footer_text, size=Pt(9), color=COLORS["slate_gray"],
                 italic=True, alignment=PP_ALIGN.LEFT)


def _add_header_bar(slide, title_text):
    """Add a deep navy header bar across the top with Georgia title in white."""
    bar_height = Inches(1.1)
    _add_rect(slide, Inches(0), Inches(0), SLIDE_WIDTH, bar_height,
              fill_color=COLORS["deep_navy"])
    _add_textbox(slide, MARGIN + Inches(0.2), Inches(0.3), Inches(10), Inches(0.5),
                 title_text, size=Pt(28), color=COLORS["white"], bold=True,
                 font_family=FONT_TITLE)
    # Teal accent line below header bar
    _add_teal_accent_line(slide, Inches(0), bar_height, SLIDE_WIDTH)


def _add_multiline_textbox(slide, left, top, width, height, lines,
                           size=Pt(11), color=None, bold=False,
                           bullet_color=None, font_family=None):
    """Add a text box with multiple lines/paragraphs."""
    if font_family is None:
        font_family = FONT_BODY
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    tf.auto_size = None

    for i, line_text in enumerate(lines):
        if i == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()
        p.text = str(line_text)
        p.font.size = size
        p.font.name = font_family
        p.font.bold = bold
        p.space_before = Pt(2)
        p.space_after = Pt(2)
        if color:
            p.font.color.rgb = color
        if bullet_color:
            p.font.color.rgb = bullet_color
    return txBox


def _severity_color(severity):
    """Get color for a severity level."""
    key = f"severity_{severity}"
    return COLORS.get(key, COLORS["severity_moderate"])


def _impact_color(impact):
    """Get color for an impact level."""
    key = f"impact_{impact}"
    return COLORS.get(key, COLORS["impact_medium"])


# ---------------------------------------------------------------------------
# Slide builders
# ---------------------------------------------------------------------------

def _add_title_slide(prs, slide_data):
    """Slide 1: Title slide — full dark navy, Georgia title centered upper-third.

    Layout: Title Slide (Dark) per template spec.
    """
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # Blank layout
    _set_slide_bg(slide, COLORS["deep_navy"])

    # Course/presentation title — Georgia 40pt, white, centered upper-third
    title = slide_data.get("presentation_title", "Gap Analysis Report")
    _add_textbox(slide, Inches(1), Inches(2.0), Inches(11.333), Inches(1.2),
                 title, size=Pt(40), color=COLORS["white"], bold=True,
                 font_family=FONT_TITLE, alignment=PP_ALIGN.CENTER)

    # Subtitle — Calibri 18pt, teal, centered
    _add_textbox(slide, Inches(1), Inches(3.4), Inches(11.333), Inches(0.5),
                 "Curriculum Gap Analysis Report", size=Pt(18),
                 color=COLORS["teal"], alignment=PP_ALIGN.CENTER)

    # Teal gradient-style accent line across bottom third
    _add_teal_accent_line(slide, Inches(3), Inches(4.2), Inches(7.333))

    # Footer — "Powered by CR8 | [Date]" in 9pt slate
    date_str = datetime.now().strftime("%B %d, %Y")
    _add_textbox(slide, Inches(1), Inches(6.5), Inches(11.333), Inches(0.4),
                 f"Powered by CR8  |  {date_str}", size=Pt(9),
                 color=COLORS["slate_gray"], alignment=PP_ALIGN.CENTER)


def _add_section_divider(prs, section_number, section_title):
    """Section divider slide — dark navy with gold section number and Georgia title.

    Layout: Section Divider per template spec.
    """
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(slide, COLORS["deep_navy"])

    # Large section number — Calibri 72pt bold, gold, left-aligned
    _add_textbox(slide, MARGIN + Inches(0.5), Inches(2.0), Inches(3), Inches(1.2),
                 str(section_number), size=Pt(72), color=COLORS["warm_gold"],
                 bold=True, font_family=FONT_BODY, alignment=PP_ALIGN.LEFT)

    # Section title — Georgia 32pt, white, below number
    _add_textbox(slide, MARGIN + Inches(0.5), Inches(3.4), Inches(10), Inches(0.8),
                 section_title, size=Pt(32), color=COLORS["white"],
                 bold=True, font_family=FONT_TITLE, alignment=PP_ALIGN.LEFT)

    # Thin teal accent line underneath title
    _add_teal_accent_line(slide, MARGIN + Inches(0.5), Inches(4.4), Inches(6))


def _add_executive_summary_slide(prs, slide_data):
    """Slide 2: Executive summary with Key Stats callout cards.

    Layout: Key Stats / Data Callout per template spec — big numbers
    in teal-tinted cards with descriptors below.
    """
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(slide, COLORS["off_white"])
    _add_header_bar(slide, "Executive Summary")

    exec_summary = slide_data.get("executive_summary", {})
    assessment = exec_summary.get("overall_assessment", "")
    critical_gaps = exec_summary.get("critical_gaps", [])
    total_gaps = exec_summary.get("total_gaps_found", 0)
    topic_count = len(slide_data.get("topic_slides", []))

    # --- KPI stat cards row (Key Stats layout) ---
    card_width = Inches(3.5)
    card_height = Inches(1.8)
    card_y = Inches(1.5)
    card_gap = Inches(0.5)
    cards_total_width = card_width * 3 + card_gap * 2
    card_start_x = (SLIDE_WIDTH - cards_total_width) / 2

    # Card 1: Total Gaps — teal number in teal-tinted card
    c1_x = card_start_x
    _add_rounded_rect(slide, c1_x, card_y, card_width, card_height, COLORS["teal_tint"])
    _add_textbox(slide, c1_x, card_y + Inches(0.2), card_width, Inches(0.8),
                 str(total_gaps), size=Pt(48), color=COLORS["teal"], bold=True,
                 alignment=PP_ALIGN.CENTER, font_family=FONT_BODY)
    _add_textbox(slide, c1_x, card_y + Inches(1.1), card_width, Inches(0.4),
                 "Gaps Identified", size=Pt(13), color=COLORS["slate_gray"],
                 alignment=PP_ALIGN.CENTER)

    # Card 2: Topics Analyzed — gold number in gold-tinted card
    c2_x = c1_x + card_width + card_gap
    _add_rounded_rect(slide, c2_x, card_y, card_width, card_height, COLORS["gold_tint"])
    _add_textbox(slide, c2_x, card_y + Inches(0.2), card_width, Inches(0.8),
                 str(topic_count), size=Pt(48), color=COLORS["warm_gold"], bold=True,
                 alignment=PP_ALIGN.CENTER, font_family=FONT_BODY)
    _add_textbox(slide, c2_x, card_y + Inches(1.1), card_width, Inches(0.4),
                 "Topics Analyzed", size=Pt(13), color=COLORS["slate_gray"],
                 alignment=PP_ALIGN.CENTER)

    # Card 3: Critical Gaps count — teal number in teal-tinted card
    critical_count = len(critical_gaps)
    c3_x = c2_x + card_width + card_gap
    _add_rounded_rect(slide, c3_x, card_y, card_width, card_height, COLORS["teal_tint"])
    _add_textbox(slide, c3_x, card_y + Inches(0.2), card_width, Inches(0.8),
                 str(critical_count), size=Pt(48), color=COLORS["teal"], bold=True,
                 alignment=PP_ALIGN.CENTER, font_family=FONT_BODY)
    _add_textbox(slide, c3_x, card_y + Inches(1.1), card_width, Inches(0.4),
                 "Critical Gaps", size=Pt(13), color=COLORS["slate_gray"],
                 alignment=PP_ALIGN.CENTER)

    # --- Assessment text below cards ---
    _add_textbox(slide, MARGIN + Inches(0.2), Inches(3.7), Inches(12), Inches(0.25),
                 "OVERALL ASSESSMENT", size=Pt(10), color=COLORS["slate_gray"],
                 bold=True)
    _add_textbox(slide, MARGIN + Inches(0.2), Inches(4.0), Inches(12), Inches(0.8),
                 assessment, size=Pt(14), color=COLORS["charcoal"])

    # --- Critical gaps list ---
    if critical_gaps:
        _add_textbox(slide, MARGIN + Inches(0.2), Inches(5.0), Inches(3), Inches(0.25),
                     "CRITICAL GAPS", size=Pt(10), color=COLORS["severity_critical"],
                     bold=True)
        y = Inches(5.35)
        for gap in critical_gaps[:5]:
            _add_oval(slide, MARGIN + Inches(0.3), y + Inches(0.05), Inches(0.12), Inches(0.12),
                      COLORS["teal"])
            _add_textbox(slide, MARGIN + Inches(0.6), y - Inches(0.02), Inches(11), Inches(0.3),
                         gap, size=Pt(12), color=COLORS["charcoal"])
            y += Inches(0.35)

    _add_footer(slide)


def _add_severity_overview_slide(prs, slide_data):
    """Severity scorecard — one row per topic with colored severity badges.

    Layout: Full Width Content per template spec.
    """
    topics = slide_data.get("topic_slides", [])
    if not topics:
        return

    page_size = 10
    pages = [topics[i:i + page_size] for i in range(0, len(topics), page_size)]

    for page_idx, page_topics in enumerate(pages):
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        _set_slide_bg(slide, COLORS["off_white"])

        title = "Gap Severity Overview"
        if len(pages) > 1:
            title += f" ({page_idx + 1}/{len(pages)})"
        _add_header_bar(slide, title)

        # Column headers
        y_header = Inches(1.3)
        _add_textbox(slide, MARGIN + Inches(0.2), y_header, Inches(5), Inches(0.3),
                     "TOPIC", size=Pt(9), color=COLORS["slate_gray"], bold=True)
        _add_textbox(slide, Inches(7.0), y_header, Inches(2), Inches(0.3),
                     "SEVERITY", size=Pt(9), color=COLORS["slate_gray"], bold=True)
        _add_textbox(slide, Inches(9.5), y_header, Inches(2), Inches(0.3),
                     "GAPS", size=Pt(9), color=COLORS["slate_gray"], bold=True)

        _add_separator_line(slide, MARGIN + Inches(0.2), Inches(1.65), Inches(12))

        y_start = Inches(1.85)
        row_height = Inches(0.55)

        for i, topic in enumerate(page_topics):
            y = y_start + i * row_height
            name = topic.get("topic_name", "Unknown")
            severity = topic.get("severity", "moderate")
            gap_count = len(topic.get("gaps", []))

            # Alternating row background
            if i % 2 == 0:
                _add_rect(slide, MARGIN, y - Inches(0.02), Inches(12.333),
                          row_height, fill_color=COLORS["teal_tint"])

            # Topic name
            _add_textbox(slide, MARGIN + Inches(0.2), y + Inches(0.08), Inches(6), Inches(0.35),
                         name, size=Pt(12), color=COLORS["charcoal"], bold=True)

            # Severity badge
            _add_badge(slide, Inches(7.0), y + Inches(0.08), Inches(1.5), Inches(0.35),
                       severity.upper(), _severity_color(severity))

            # Gap count
            gap_label = f"{gap_count} gap{'s' if gap_count != 1 else ''}"
            _add_textbox(slide, Inches(9.5), y + Inches(0.08), Inches(2), Inches(0.35),
                         gap_label, size=Pt(12), color=COLORS["slate_gray"])

        _add_footer(slide)


def _add_topic_slide(prs, topic_data):
    """Per-topic gap detail slide — Market Intelligence Spotlight layout.

    Left half: dark navy background with gold "Market Signal" label + key finding.
    Right half: off-white with curriculum context, gaps, and recommendations.
    Teal accent bar on the right column border.
    """
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    slide_title = topic_data.get("slide_title", topic_data.get("topic_name", ""))
    severity = topic_data.get("severity", "moderate")
    curriculum_summary = topic_data.get("curriculum_summary", "")
    industry_summary = topic_data.get("industry_summary", "")
    gaps = topic_data.get("gaps", [])
    recommendations = topic_data.get("top_recommendations", [])

    # --- Left half: Dark navy panel (Market Intelligence Spotlight) ---
    left_panel_width = Inches(6.0)
    _add_rect(slide, Inches(0), Inches(0), left_panel_width, SLIDE_HEIGHT,
              fill_color=COLORS["deep_navy"])

    # Gold "Market Signal" label
    _add_textbox(slide, MARGIN + Inches(0.2), MARGIN + Inches(0.2), Inches(4), Inches(0.35),
                 "MARKET SIGNAL", size=Pt(10), color=COLORS["warm_gold"],
                 bold=True)

    # Topic title — Georgia, white
    _add_textbox(slide, MARGIN + Inches(0.2), MARGIN + Inches(0.7), Inches(5), Inches(0.8),
                 slide_title, size=Pt(28), color=COLORS["white"],
                 bold=True, font_family=FONT_TITLE)

    # Severity badge
    _add_badge(slide, MARGIN + Inches(0.2), Inches(2.0), Inches(1.6), Inches(0.35),
               severity.upper(), _severity_color(severity))

    # Teal accent line
    _add_teal_accent_line(slide, MARGIN + Inches(0.2), Inches(2.7), Inches(4))

    # Industry demands (what the market expects) — white text on navy
    _add_textbox(slide, MARGIN + Inches(0.2), Inches(3.0), Inches(5), Inches(0.25),
                 "WHAT INDUSTRY EXPECTS", size=Pt(9), color=COLORS["teal"],
                 bold=True)
    _add_textbox(slide, MARGIN + Inches(0.2), Inches(3.35), Inches(5), Inches(1.2),
                 industry_summary, size=Pt(14), color=COLORS["white"])

    # Gap list on left panel
    if gaps:
        _add_textbox(slide, MARGIN + Inches(0.2), Inches(4.7), Inches(5), Inches(0.25),
                     "IDENTIFIED GAPS", size=Pt(9), color=COLORS["warm_gold"],
                     bold=True)
        y = Inches(5.05)
        for gap in gaps[:4]:
            impact = gap.get("impact", "medium")
            gap_title = gap.get("gap_title", "")
            _add_oval(slide, MARGIN + Inches(0.3), y + Inches(0.04),
                      Inches(0.12), Inches(0.12), _impact_color(impact))
            _add_textbox(slide, MARGIN + Inches(0.55), y - Inches(0.02),
                         Inches(4.5), Inches(0.3),
                         gap_title, size=Pt(11), color=COLORS["white"])
            y += Inches(0.35)

    # --- Teal vertical accent bar at boundary ---
    _add_teal_accent_bar(slide, left_panel_width, Inches(0), SLIDE_HEIGHT)

    # --- Right half: Off-white panel ---
    right_x = left_panel_width + Inches(0.1)
    right_content_x = right_x + MARGIN
    right_width = SLIDE_WIDTH - right_x - MARGIN

    _add_rect(slide, right_x, Inches(0), SLIDE_WIDTH - right_x, SLIDE_HEIGHT,
              fill_color=COLORS["off_white"])

    # Curriculum coverage — what the PDF module covers
    _add_textbox(slide, right_content_x, MARGIN + Inches(0.2), right_width, Inches(0.25),
                 "WHAT THE CURRICULUM COVERS", size=Pt(9),
                 color=COLORS["slate_gray"], bold=True)
    _add_textbox(slide, right_content_x, MARGIN + Inches(0.55), right_width, Inches(1.5),
                 curriculum_summary, size=Pt(12), color=COLORS["charcoal"])

    _add_separator_line(slide, right_content_x, Inches(2.5), right_width - Inches(0.3))

    # Gap details on right panel (descriptions)
    if gaps:
        _add_textbox(slide, right_content_x, Inches(2.7), right_width, Inches(0.25),
                     "GAP DETAILS", size=Pt(9), color=COLORS["slate_gray"],
                     bold=True)
        y = Inches(3.05)
        for gap in gaps[:4]:
            description = gap.get("description", "")
            gap_title = gap.get("gap_title", "")
            impact = gap.get("impact", "medium")

            # Impact dot + title
            _add_oval(slide, right_content_x, y + Inches(0.04),
                      Inches(0.12), Inches(0.12), _impact_color(impact))
            _add_textbox(slide, right_content_x + Inches(0.22), y - Inches(0.02),
                         right_width - Inches(0.3), Inches(0.25),
                         gap_title, size=Pt(11), color=COLORS["charcoal"], bold=True)
            # Description
            _add_textbox(slide, right_content_x + Inches(0.22), y + Inches(0.22),
                         right_width - Inches(0.3), Inches(0.4),
                         description, size=Pt(9), color=COLORS["slate_gray"])
            y += Inches(0.7)

    # Recommendations strip at bottom of right panel
    if recommendations:
        rec_y = Inches(5.8)
        _add_rect(slide, right_x, rec_y, SLIDE_WIDTH - right_x, Inches(1.3),
                  fill_color=COLORS["teal_tint"])
        _add_textbox(slide, right_content_x, rec_y + Inches(0.1), right_width, Inches(0.25),
                     "RECOMMENDATIONS", size=Pt(9), color=COLORS["teal"], bold=True)
        rec_text = "  |  ".join(recommendations[:3])
        _add_textbox(slide, right_content_x, rec_y + Inches(0.4), right_width, Inches(0.7),
                     rec_text, size=Pt(11), color=COLORS["charcoal"])

    # Footer on right panel
    date_str = datetime.now().strftime("%B %d, %Y")
    _add_textbox(slide, right_content_x, FOOTER_ZONE_TOP, right_width, FOOTER_HEIGHT,
                 f"Powered by CR8  |  {date_str}", size=Pt(9),
                 color=COLORS["slate_gray"], italic=True)


def _add_recommendations_slide(prs, slide_data):
    """Consolidated recommendations with priority badges.

    Layout: Full Width Content per template spec — teal accent below title.
    """
    recs = slide_data.get("recommendations_summary", [])
    if not recs:
        return

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(slide, COLORS["off_white"])
    _add_header_bar(slide, "Recommendations & Next Steps")

    # Sort by priority
    priority_order = {"high": 0, "medium": 1, "low": 2}
    recs_sorted = sorted(recs, key=lambda r: priority_order.get(r.get("priority", "low"), 2))

    y = Inches(1.5)
    for rec in recs_sorted[:10]:
        priority = rec.get("priority", "medium")
        action = rec.get("action", "")
        affected = rec.get("topics_affected", [])

        # Teal priority stripe on left
        stripe_color = _impact_color(priority)
        _add_rect(slide, MARGIN + Inches(0.2), y, Inches(0.08), Inches(0.5),
                  fill_color=stripe_color)

        # Priority badge
        _add_badge(slide, MARGIN + Inches(0.5), y + Inches(0.05), Inches(1.1), Inches(0.35),
                   priority.upper(), stripe_color)

        # Action text
        _add_textbox(slide, Inches(2.3), y, Inches(7), Inches(0.35),
                     action, size=Pt(13), color=COLORS["charcoal"], bold=True)

        # Affected topics
        if affected:
            topics_text = f"Affects: {', '.join(affected[:4])}"
            _add_textbox(slide, Inches(2.3), y + Inches(0.35), Inches(7), Inches(0.25),
                         topics_text, size=Pt(9), color=COLORS["slate_gray"], italic=True)

        y += Inches(0.75)

    _add_footer(slide)


def _add_closing_slide(prs, slide_data):
    """Closing slide — Summary/Takeaway layout per template spec.

    Dark navy background, gold "Key Takeaways" heading,
    numbered points with teal circle icons, CR8 branding.
    """
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(slide, COLORS["deep_navy"])

    # Gold heading — "Key Takeaways"
    _add_textbox(slide, MARGIN + Inches(0.5), Inches(0.8), Inches(11), Inches(0.8),
                 "Key Takeaways", size=Pt(36), color=COLORS["warm_gold"],
                 bold=True, font_family=FONT_TITLE, alignment=PP_ALIGN.LEFT)

    _add_teal_accent_line(slide, MARGIN + Inches(0.5), Inches(1.7), Inches(5))

    # Build takeaway points from slide data
    takeaways = []
    exec_summary = slide_data.get("executive_summary", {})
    assessment = exec_summary.get("overall_assessment", "")
    if assessment:
        takeaways.append(assessment)

    critical_gaps = exec_summary.get("critical_gaps", [])
    if critical_gaps:
        takeaways.append(f"Top gap: {critical_gaps[0]}")

    recs = slide_data.get("recommendations_summary", [])
    high_priority = [r.get("action", "") for r in recs if r.get("priority") == "high"]
    for action in high_priority[:3]:
        takeaways.append(action)

    # Pad to 3–5 points
    if not takeaways:
        takeaways = ["Review identified gaps and prioritize curriculum updates"]

    # Numbered points with teal circle icons
    y = Inches(2.2)
    for i, point in enumerate(takeaways[:5]):
        # Teal circle icon with number
        circle = _add_oval(slide, MARGIN + Inches(0.5), y + Inches(0.02),
                           Inches(0.35), Inches(0.35), COLORS["teal"])
        tf = circle.text_frame
        tf.word_wrap = False
        p = tf.paragraphs[0]
        p.text = str(i + 1)
        p.font.size = Pt(12)
        p.font.bold = True
        p.font.color.rgb = COLORS["white"]
        p.font.name = FONT_BODY
        p.alignment = PP_ALIGN.CENTER
        tf.margin_left = Pt(0)
        tf.margin_right = Pt(0)
        tf.margin_top = Pt(0)
        tf.margin_bottom = Pt(0)

        # Point text — white Calibri 16pt
        _add_textbox(slide, MARGIN + Inches(1.1), y, Inches(10.5), Inches(0.4),
                     point, size=Pt(16), color=COLORS["white"])
        y += Inches(0.7)

    # CR8 branding in footer
    _add_textbox(slide, Inches(1), Inches(6.5), Inches(11.333), Inches(0.4),
                 "Powered by CR8", size=Pt(12),
                 color=COLORS["slate_gray"], alignment=PP_ALIGN.CENTER)

    date_str = datetime.now().strftime("%B %d, %Y")
    _add_textbox(slide, Inches(1), Inches(6.9), Inches(11.333), Inches(0.4),
                 date_str, size=Pt(10), color=COLORS["slate_gray"],
                 alignment=PP_ALIGN.CENTER)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_gap_ppt(slide_data: dict, output_path: str) -> str:
    """Build a Gap Analysis PowerPoint from structured slide data.

    Uses the CR8 "Midnight Teal" design system with 8 slide master types:
    1. Title Slide (Dark)
    2. Section Divider (before first topic group)
    3. Executive Summary (Key Stats layout)
    4. Severity Overview (Full Width Content)
    5. Market Intelligence Spotlight (per-topic gap detail)
    6. Recommendations (Full Width Content)
    7. Summary/Takeaway (closing)

    Args:
        slide_data: Structured JSON from the LLM with presentation_title,
                    executive_summary, topic_slides, and recommendations_summary.
        output_path: Where to save the .pptx file.

    Returns:
        The output_path for convenience.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    prs = Presentation()
    prs.slide_width = SLIDE_WIDTH
    prs.slide_height = SLIDE_HEIGHT

    # 1. Title slide
    _add_title_slide(prs, slide_data)

    # 2. Executive summary (Key Stats layout)
    _add_executive_summary_slide(prs, slide_data)

    # 3. Severity overview
    _add_severity_overview_slide(prs, slide_data)

    # 4. Section divider before topics
    topic_slides = slide_data.get("topic_slides", [])
    if topic_slides:
        _add_section_divider(prs, 1, "Gap Analysis by Topic")

    # 5. Per-topic Market Intelligence Spotlight slides
    for topic in topic_slides:
        _add_topic_slide(prs, topic)

    # 6. Section divider before recommendations
    recs = slide_data.get("recommendations_summary", [])
    if recs:
        _add_section_divider(prs, 2, "Recommendations & Next Steps")

    # 7. Recommendations
    _add_recommendations_slide(prs, slide_data)

    # 8. Summary/Takeaway (closing)
    _add_closing_slide(prs, slide_data)

    prs.save(output_path)
    return output_path
