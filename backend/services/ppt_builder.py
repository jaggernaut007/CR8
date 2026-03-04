"""Teaching PowerPoint builder using python-pptx + matplotlib.

Generates a professional widescreen (16:9) presentation that TEACHES
industry-relevant concepts with diagrams and infographics, using the CR8
"Midnight Teal" design language with Georgia + Calibri typography.

Slide types:
  1. Title Slide (Dark)
  2. Course Overview (Key Stats with priority breakdown)
  3. Coverage Radar Chart (matplotlib: curriculum vs industry scores)
  4. Topics Overview (scorecard table)
  5. Section Divider
  6–N. Per-topic slide groups:
      a. Topic Teaching Slide (assertion-evidence, diagrams, misconceptions)
      b. Market Intelligence Spotlight (split layout: signal + context)
      c. Quiz / Reflection Slide (retrieval practice with A-D options)
  N+1. Section Divider
  N+2. Recommendations (with process flow)
  N+3. Closing (Key Takeaways)

Design reference: Docs/CR8_Course_PPT_Template_Recommendation.md
"""

import io
import os
from datetime import datetime

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend — no GUI needed
import matplotlib.pyplot as plt
import numpy as np

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

from backend.services.pdf_builder import _strip_latex

# ---------------------------------------------------------------------------
# Design tokens — "Midnight Teal" CR8 palette
# ---------------------------------------------------------------------------
COLORS = {
    # Primary palette
    "deep_navy": RGBColor(0x0D, 0x1B, 0x2A),
    "teal": RGBColor(0x1B, 0x99, 0x8B),
    "warm_gold": RGBColor(0xF4, 0xB9, 0x42),
    "off_white": RGBColor(0xF7, 0xF7, 0xF2),
    "charcoal": RGBColor(0x2D, 0x34, 0x36),
    "slate_gray": RGBColor(0x63, 0x6E, 0x72),
    "white": RGBColor(0xFF, 0xFF, 0xFF),
    # Tinted backgrounds
    "teal_tint": RGBColor(0xE6, 0xF5, 0xF3),
    "gold_tint": RGBColor(0xFE, 0xF6, 0xE2),
    # Priority / Relevance
    "priority_essential": RGBColor(0x1B, 0x99, 0x8B),   # teal — important, not alarming
    "priority_recommended": RGBColor(0xF4, 0xB9, 0x42),  # gold
    "priority_supplementary": RGBColor(0x63, 0x6E, 0x72), # slate
    "impact_high": RGBColor(0x1B, 0x99, 0x8B),
    "impact_medium": RGBColor(0xF4, 0xB9, 0x42),
    "impact_low": RGBColor(0x63, 0x6E, 0x72),
    # Misconception callout colors
    "wrong_bg": RGBColor(0xFD, 0xE8, 0xE8),   # light red tint
    "right_bg": RGBColor(0xE8, 0xF5, 0xE9),   # light green tint
    "wrong_text": RGBColor(0xC6, 0x28, 0x28),  # dark red
    "right_text": RGBColor(0x2E, 0x7D, 0x32),  # dark green
}

# Matplotlib-compatible RGB tuples (0-1 range)
_MPL_TEAL = (0x1B / 255, 0x99 / 255, 0x8B / 255)
_MPL_GOLD = (0xF4 / 255, 0xB9 / 255, 0x42 / 255)
_MPL_NAVY = (0x0D / 255, 0x1B / 255, 0x2A / 255)
_MPL_CHARCOAL = (0x2D / 255, 0x34 / 255, 0x36 / 255)

# Typography
FONT_TITLE = "Georgia"
FONT_BODY = "Calibri"

# Slide dimensions (widescreen 16:9)
SLIDE_WIDTH = Inches(13.333)
SLIDE_HEIGHT = Inches(7.5)

# Layout constants
MARGIN = Inches(0.5)
CONTENT_GAP = Inches(0.3)
TITLE_ZONE_BOTTOM = Inches(1.5)
FOOTER_ZONE_TOP = Inches(7.1)
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
    p.text = _strip_latex(str(text))
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
    """Add a 4pt wide vertical teal accent bar."""
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
        p.text = _strip_latex(str(line_text))
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
    """Get color for a severity/importance level."""
    mapping = {
        "critical": COLORS["priority_essential"],
        "moderate": COLORS["priority_recommended"],
        "minor": COLORS["priority_supplementary"],
    }
    return mapping.get(severity, COLORS["priority_recommended"])


def _severity_label(severity):
    """Map internal severity to user-facing importance label."""
    mapping = {
        "critical": "ESSENTIAL",
        "moderate": "RECOMMENDED",
        "minor": "SUPPLEMENTARY",
    }
    return mapping.get(severity, "RECOMMENDED")


def _impact_color(impact):
    """Get color for an impact/relevance level."""
    key = f"impact_{impact}"
    return COLORS.get(key, COLORS["impact_medium"])


# ---------------------------------------------------------------------------
# Diagram helpers
# ---------------------------------------------------------------------------

def _add_process_flow_diagram(slide, x, y, width, height, nodes, node_colors=None):
    """Render a left-to-right process flow: rounded rectangles connected by arrows."""
    if not nodes:
        return
    n = len(nodes)
    if node_colors is None:
        node_colors = [COLORS["teal"]] * n

    arrow_width = Inches(0.3)
    total_arrows = max(n - 1, 0)
    arrows_total = arrow_width * total_arrows
    node_width = (width - arrows_total) / n
    node_height = min(height, Inches(0.7))
    node_y = y + (height - node_height) / 2

    for i, label in enumerate(nodes):
        nx = x + i * (node_width + arrow_width)
        color = node_colors[i] if i < len(node_colors) else COLORS["teal"]

        # Node rectangle
        shape = _add_rounded_rect(slide, nx, node_y, node_width, node_height, color)
        tf = shape.text_frame
        tf.word_wrap = True
        tf.margin_left = Pt(4)
        tf.margin_right = Pt(4)
        tf.margin_top = Pt(2)
        tf.margin_bottom = Pt(2)
        p = tf.paragraphs[0]
        p.text = str(label)
        p.font.size = Pt(9)
        p.font.bold = True
        p.font.color.rgb = COLORS["white"]
        p.font.name = FONT_BODY
        p.alignment = PP_ALIGN.CENTER

        # Arrow between nodes
        if i < n - 1:
            ax = nx + node_width
            ay = node_y + node_height / 2 - Inches(0.12)
            arrow = slide.shapes.add_shape(
                MSO_SHAPE.RIGHT_ARROW, ax, ay, arrow_width, Inches(0.24)
            )
            arrow.fill.solid()
            arrow.fill.fore_color.rgb = COLORS["slate_gray"]
            arrow.line.fill.background()


def _add_comparison_diagram(slide, x, y, width, height,
                            left_items, right_items,
                            left_title="Curriculum", right_title="Industry"):
    """Render a two-column comparison diagram.

    Adapts spacing based on available width and number of items.
    """
    gutter = Inches(0.2)
    col_width = (width - gutter) / 2
    right_x = x + col_width + gutter
    header_h = Inches(0.32)

    # Left column header
    _add_rounded_rect(slide, x, y, col_width, header_h, COLORS["slate_gray"])
    _add_textbox(slide, x, y + Inches(0.03), col_width, Inches(0.25),
                 left_title, size=Pt(9), color=COLORS["white"], bold=True,
                 alignment=PP_ALIGN.CENTER)

    # Right column header
    _add_rounded_rect(slide, right_x, y, col_width, header_h, COLORS["teal"])
    _add_textbox(slide, right_x, y + Inches(0.03), col_width, Inches(0.25),
                 right_title, size=Pt(9), color=COLORS["white"], bold=True,
                 alignment=PP_ALIGN.CENTER)

    # Calculate row spacing based on available height and item count
    max_items = max(len(left_items), len(right_items), 1)
    items_to_show = min(max_items, 4)  # Cap at 4 items
    available_h = height - header_h - Inches(0.08)
    row_h = min(available_h / items_to_show, Inches(0.28))
    items_start_y = y + header_h + Inches(0.06)

    # Left items
    for i, item in enumerate(left_items[:items_to_show]):
        iy = items_start_y + i * row_h
        _add_textbox(slide, x + Inches(0.08), iy, col_width - Inches(0.16), row_h,
                     item, size=Pt(8), color=COLORS["charcoal"])

    # Right items
    for i, item in enumerate(right_items[:items_to_show]):
        iy = items_start_y + i * row_h
        _add_textbox(slide, right_x + Inches(0.08), iy, col_width - Inches(0.16), row_h,
                     item, size=Pt(8), color=COLORS["charcoal"])


def _add_concept_map_diagram(slide, x, y, width, height, center_label, satellite_labels):
    """Render a concept map as a clean tree diagram.

    Layout:
        [Center] ──── ┬── [Satellite 1]
                      ├── [Satellite 2]
                      └── [Satellite 3]

    Uses a trunk + spine + branch pattern that looks like a proper
    mind map and works reliably in constrained spaces.
    """
    if not satellite_labels:
        return

    n = min(len(satellite_labels), 5)
    line_weight = Pt(2)

    # --- Center node (left, vertically centered) ---
    center_w = min(Inches(1.5), width * 0.28)
    center_h = Inches(0.45)
    cx = x
    cy = y + (height - center_h) / 2

    center_shape = _add_rounded_rect(slide, cx, cy, center_w, center_h, COLORS["deep_navy"])
    tf = center_shape.text_frame
    tf.word_wrap = True
    tf.margin_left = Pt(4)
    tf.margin_right = Pt(4)
    tf.margin_top = Pt(2)
    tf.margin_bottom = Pt(2)
    p = tf.paragraphs[0]
    p.text = str(center_label)
    p.font.size = Pt(9)
    p.font.bold = True
    p.font.color.rgb = COLORS["white"]
    p.font.name = FONT_BODY
    p.alignment = PP_ALIGN.CENTER

    # --- Satellites (stacked on the right) ---
    spine_x = cx + center_w + Inches(0.35)  # vertical spine position
    sat_x = spine_x + Inches(0.2)           # satellites start after spine
    sat_w = min(width - (sat_x - x) - Inches(0.05), Inches(2.8))
    sat_h = Inches(0.28)
    sat_gap = Inches(0.06)
    total_sat_height = n * sat_h + (n - 1) * sat_gap
    sat_start_y = y + (height - total_sat_height) / 2

    # --- Trunk line: horizontal from center right edge to spine ---
    hub_y = cy + center_h / 2
    trunk = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        cx + center_w, hub_y - Pt(1),
        spine_x - (cx + center_w), line_weight
    )
    trunk.fill.solid()
    trunk.fill.fore_color.rgb = COLORS["teal"]
    trunk.line.fill.background()

    # --- Vertical spine: connects top satellite to bottom satellite ---
    first_sat_center_y = sat_start_y + sat_h / 2
    last_sat_center_y = sat_start_y + (n - 1) * (sat_h + sat_gap) + sat_h / 2
    spine_top = min(first_sat_center_y, hub_y)
    spine_bottom = max(last_sat_center_y, hub_y)

    spine = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        spine_x - Pt(1), spine_top,
        line_weight, spine_bottom - spine_top
    )
    spine.fill.solid()
    spine.fill.fore_color.rgb = COLORS["teal"]
    spine.line.fill.background()

    # --- Branch lines + satellite nodes ---
    for i, label in enumerate(satellite_labels[:n]):
        sy = sat_start_y + i * (sat_h + sat_gap)
        branch_y = sy + sat_h / 2

        # Horizontal branch from spine to satellite
        branch = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            spine_x, branch_y - Pt(1),
            sat_x - spine_x, line_weight
        )
        branch.fill.solid()
        branch.fill.fore_color.rgb = COLORS["teal"]
        branch.line.fill.background()

        # Satellite node
        sat_shape = _add_rounded_rect(slide, sat_x, sy, sat_w, sat_h, COLORS["teal"])
        tf = sat_shape.text_frame
        tf.word_wrap = True
        tf.margin_left = Pt(4)
        tf.margin_right = Pt(4)
        tf.margin_top = Pt(1)
        tf.margin_bottom = Pt(1)
        p = tf.paragraphs[0]
        p.text = str(label)
        p.font.size = Pt(8)
        p.font.bold = True
        p.font.color.rgb = COLORS["white"]
        p.font.name = FONT_BODY
        p.alignment = PP_ALIGN.CENTER


# ---------------------------------------------------------------------------
# Radar chart (matplotlib)
# ---------------------------------------------------------------------------

def _generate_radar_chart(topic_scores):
    """Generate a radar chart PNG comparing curriculum vs industry scores."""
    if not topic_scores:
        return None

    labels = [s.get("topic", "?") for s in topic_scores]
    curriculum = [s.get("curriculum_score", 50) for s in topic_scores]
    industry = [s.get("industry_requirement", 80) for s in topic_scores]

    # Truncate long labels
    labels = [lbl[:18] + "..." if len(lbl) > 18 else lbl for lbl in labels]

    n = len(labels)
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()
    angles += angles[:1]
    curriculum += curriculum[:1]
    industry += industry[:1]

    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
    fig.patch.set_alpha(0)
    ax.patch.set_alpha(0)

    # Industry requirement (outer polygon — gold)
    ax.fill(angles, industry, alpha=0.15, color=_MPL_GOLD)
    ax.plot(angles, industry, color=_MPL_GOLD, linewidth=2, label="Industry Standard")

    # Curriculum coverage (inner polygon — teal)
    ax.fill(angles, curriculum, alpha=0.25, color=_MPL_TEAL)
    ax.plot(angles, curriculum, color=_MPL_TEAL, linewidth=2, label="Your Course")

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=8, color=_MPL_CHARCOAL)
    ax.set_ylim(0, 100)
    ax.set_yticks([25, 50, 75, 100])
    ax.set_yticklabels(["25", "50", "75", "100"], fontsize=7, color=_MPL_CHARCOAL)
    ax.spines["polar"].set_color(_MPL_CHARCOAL)
    ax.tick_params(colors=_MPL_CHARCOAL)
    ax.grid(color=_MPL_CHARCOAL, alpha=0.2)

    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1), fontsize=9,
              framealpha=0.9, edgecolor=_MPL_CHARCOAL)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=144, bbox_inches="tight",
                transparent=True, pad_inches=0.3)
    plt.close(fig)
    buf.seek(0)
    return buf


# ---------------------------------------------------------------------------
# Slide builders
# ---------------------------------------------------------------------------

def _add_title_slide(prs, slide_data):
    """Slide 1: Title slide — full dark navy, Georgia title centered."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # Blank layout
    _set_slide_bg(slide, COLORS["deep_navy"])

    title = slide_data.get("presentation_title", "Course Supplement")
    _add_textbox(slide, Inches(1), Inches(2.0), Inches(11.333), Inches(1.5),
                 title, size=Pt(40), color=COLORS["white"], bold=True,
                 font_family=FONT_TITLE, alignment=PP_ALIGN.CENTER)

    _add_teal_accent_line(slide, Inches(3), Inches(3.8), Inches(7.333))

    date_str = datetime.now().strftime("%B %d, %Y")
    _add_textbox(slide, Inches(1), Inches(6.5), Inches(11.333), Inches(0.4),
                 f"Powered by CR8  |  {date_str}", size=Pt(9),
                 color=COLORS["slate_gray"], alignment=PP_ALIGN.CENTER)


def _add_section_divider(prs, section_number, section_title):
    """Section divider slide — dark navy with gold section number."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(slide, COLORS["deep_navy"])

    _add_textbox(slide, MARGIN + Inches(0.5), Inches(2.0), Inches(3), Inches(1.2),
                 str(section_number), size=Pt(72), color=COLORS["warm_gold"],
                 bold=True, font_family=FONT_BODY, alignment=PP_ALIGN.LEFT)

    _add_textbox(slide, MARGIN + Inches(0.5), Inches(3.4), Inches(10), Inches(0.8),
                 section_title, size=Pt(32), color=COLORS["white"],
                 bold=True, font_family=FONT_TITLE, alignment=PP_ALIGN.LEFT)

    _add_teal_accent_line(slide, MARGIN + Inches(0.5), Inches(4.4), Inches(6))


def _add_executive_summary_slide(prs, slide_data):
    """Slide 2: Course overview with priority breakdown stat cards."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(slide, COLORS["off_white"])
    _add_header_bar(slide, "Course Overview")

    exec_summary = slide_data.get("executive_summary", {})
    assessment = exec_summary.get("overall_assessment", "")
    key_takeaways = exec_summary.get("critical_gaps", [])
    total_concepts = exec_summary.get("total_gaps_found", 0)
    topics_analyzed = exec_summary.get("topics_analyzed",
                                       len(slide_data.get("topic_slides", [])))
    essential_count = exec_summary.get("critical_count", len(key_takeaways))
    recommended_count = exec_summary.get("moderate_count", 0)
    supplementary_count = exec_summary.get("minor_count", 0)

    # --- KPI stat cards row ---
    card_width = Inches(2.4)
    card_height = Inches(1.6)
    card_y = Inches(1.5)
    card_gap = Inches(0.35)
    cards = [
        (str(total_concepts), "Concepts Covered", COLORS["teal"], COLORS["teal_tint"]),
        (str(topics_analyzed), "Topics", COLORS["warm_gold"], COLORS["gold_tint"]),
        (str(essential_count), "Essential", COLORS["priority_essential"], COLORS["teal_tint"]),
        (str(recommended_count), "Recommended", COLORS["priority_recommended"], COLORS["gold_tint"]),
        (str(supplementary_count), "Supplementary", COLORS["priority_supplementary"], COLORS["teal_tint"]),
    ]
    total_width = card_width * len(cards) + card_gap * (len(cards) - 1)
    start_x = (SLIDE_WIDTH - total_width) / 2

    for i, (num, label, num_color, bg_color) in enumerate(cards):
        cx = start_x + i * (card_width + card_gap)
        _add_rounded_rect(slide, cx, card_y, card_width, card_height, bg_color)
        _add_textbox(slide, cx, card_y + Inches(0.15), card_width, Inches(0.7),
                     num, size=Pt(36), color=num_color, bold=True,
                     alignment=PP_ALIGN.CENTER, font_family=FONT_BODY)
        _add_textbox(slide, cx, card_y + Inches(0.95), card_width, Inches(0.35),
                     label, size=Pt(12), color=COLORS["slate_gray"],
                     alignment=PP_ALIGN.CENTER)

    # --- Summary text ---
    _add_textbox(slide, MARGIN + Inches(0.2), Inches(3.5), Inches(12), Inches(0.25),
                 "WHAT YOU'LL LEARN", size=Pt(10), color=COLORS["teal"],
                 bold=True)
    _add_textbox(slide, MARGIN + Inches(0.2), Inches(3.8), Inches(12), Inches(0.8),
                 assessment, size=Pt(14), color=COLORS["charcoal"])

    # --- Key areas list ---
    if key_takeaways:
        _add_textbox(slide, MARGIN + Inches(0.2), Inches(4.8), Inches(3), Inches(0.25),
                     "KEY TOPICS", size=Pt(10), color=COLORS["teal"],
                     bold=True)
        y = Inches(5.15)
        for area in key_takeaways[:5]:
            _add_oval(slide, MARGIN + Inches(0.3), y + Inches(0.05),
                      Inches(0.12), Inches(0.12), COLORS["teal"])
            _add_textbox(slide, MARGIN + Inches(0.6), y - Inches(0.02),
                         Inches(11), Inches(0.3),
                         area, size=Pt(12), color=COLORS["charcoal"])
            y += Inches(0.35)

    _add_footer(slide)


def _add_radar_chart_slide(prs, slide_data):
    """Slide 3: Radar chart — your course vs industry standards."""
    exec_summary = slide_data.get("executive_summary", {})
    topic_scores = exec_summary.get("topic_scores", [])
    if not topic_scores:
        return

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(slide, COLORS["off_white"])
    _add_header_bar(slide, "Your Course vs. Industry Standards")

    # Generate the radar chart image
    chart_buf = _generate_radar_chart(topic_scores)
    if chart_buf is None:
        return

    # Embed as image — centered, large
    chart_width = Inches(6.5)
    chart_height = Inches(5.2)
    chart_x = (SLIDE_WIDTH - chart_width) / 2
    chart_y = Inches(1.4)
    slide.shapes.add_picture(chart_buf, chart_x, chart_y, chart_width, chart_height)

    # Legend note below chart
    _add_textbox(slide, MARGIN, Inches(6.7), Inches(12), Inches(0.3),
                 "The space between your course (teal) and industry standards (gold) highlights where this supplement adds value.",
                 size=Pt(10), color=COLORS["slate_gray"], italic=True,
                 alignment=PP_ALIGN.CENTER)

    _add_footer(slide)


def _add_severity_overview_slide(prs, slide_data):
    """Topics overview — one row per topic with colored importance badges."""
    topics = slide_data.get("topic_slides", [])
    if not topics:
        return

    page_size = 10
    pages = [topics[i:i + page_size] for i in range(0, len(topics), page_size)]

    for page_idx, page_topics in enumerate(pages):
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        _set_slide_bg(slide, COLORS["off_white"])

        title = "Topics at a Glance"
        if len(pages) > 1:
            title += f" ({page_idx + 1}/{len(pages)})"
        _add_header_bar(slide, title)

        # Column headers
        y_header = Inches(1.3)
        _add_textbox(slide, MARGIN + Inches(0.2), y_header, Inches(5), Inches(0.3),
                     "TOPIC", size=Pt(9), color=COLORS["slate_gray"], bold=True)
        _add_textbox(slide, Inches(7.0), y_header, Inches(2), Inches(0.3),
                     "PRIORITY", size=Pt(9), color=COLORS["slate_gray"], bold=True)
        _add_textbox(slide, Inches(9.5), y_header, Inches(2), Inches(0.3),
                     "CONCEPTS", size=Pt(9), color=COLORS["slate_gray"], bold=True)

        _add_separator_line(slide, MARGIN + Inches(0.2), Inches(1.65), Inches(12))

        y_start = Inches(1.85)
        row_height = Inches(0.55)

        for i, topic in enumerate(page_topics):
            y = y_start + i * row_height
            name = topic.get("topic_name", "Unknown")
            severity = topic.get("severity", "moderate")
            gap_count = len(topic.get("gap_concepts", topic.get("gaps", [])))

            if i % 2 == 0:
                _add_rect(slide, MARGIN, y - Inches(0.02), Inches(12.333),
                          row_height, fill_color=COLORS["teal_tint"])

            _add_textbox(slide, MARGIN + Inches(0.2), y + Inches(0.08),
                         Inches(6), Inches(0.35),
                         name, size=Pt(12), color=COLORS["charcoal"], bold=True)

            _add_badge(slide, Inches(7.0), y + Inches(0.08),
                       Inches(1.8), Inches(0.35),
                       _severity_label(severity), _severity_color(severity))

            concept_label = f"{gap_count} concept{'s' if gap_count != 1 else ''}"
            _add_textbox(slide, Inches(9.5), y + Inches(0.08), Inches(2), Inches(0.35),
                         concept_label, size=Pt(12), color=COLORS["slate_gray"])

        _add_footer(slide)


def _add_topic_teaching_slide(prs, topic_data):
    """Per-topic teaching slide — assertion-evidence layout with diagrams.

    Layout with proper spacing:
    - Title zone: 0.3" to ~1.1" (assertion title + accent line)
    - Anchor zone: ~1.15" to ~1.55" (curriculum anchor)
    - Content zone: ~1.7" to ~5.3" (concept cards with diagrams)
    - Misconception zone: ~5.5" to ~6.5" (wrong/right callout)
    """
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(slide, COLORS["off_white"])

    slide_title = topic_data.get("slide_title", topic_data.get("topic_name", ""))
    severity = topic_data.get("severity", "moderate")
    curriculum_anchor = topic_data.get("curriculum_anchor",
                                       topic_data.get("curriculum_summary", ""))
    gap_concepts = topic_data.get("gap_concepts", [])
    misconception = topic_data.get("misconception", {})

    # --- Title zone ---
    # Assertion title (Georgia, navy) — left-aligned with breathing room
    _add_textbox(slide, MARGIN + Inches(0.3), Inches(0.35), Inches(10), Inches(0.8),
                 slide_title, size=Pt(24), color=COLORS["deep_navy"], bold=True,
                 font_family=FONT_TITLE)

    # Importance badge (top-right, subtle)
    _add_badge(slide, Inches(11.2), Inches(0.4), Inches(1.6), Inches(0.35),
               _severity_label(severity), _severity_color(severity))

    # Teal accent line below title
    _add_teal_accent_line(slide, MARGIN + Inches(0.3), Inches(1.15), Inches(4))

    # --- Anchor zone ---
    # Curriculum anchor — the "You already know..." sentence
    _add_textbox(slide, MARGIN + Inches(0.3), Inches(1.3), Inches(11.5), Inches(0.4),
                 curriculum_anchor, size=Pt(11),
                 color=COLORS["slate_gray"], italic=True)

    # --- Content zone (concepts) ---
    concept_y = Inches(1.85)
    content_height = Inches(3.4)
    concepts_to_show = gap_concepts[:2]  # Max 2 per slide for clarity

    if len(concepts_to_show) == 1:
        # Single concept — full width with generous margins
        _render_gap_concept(slide, MARGIN + Inches(0.3), concept_y,
                            Inches(11.8), content_height, concepts_to_show[0])
    elif len(concepts_to_show) >= 2:
        # Two concepts — side by side with clear separation
        col_width = Inches(5.5)
        gutter = Inches(0.8)
        left_x = MARGIN + Inches(0.3)
        right_x = left_x + col_width + gutter

        _render_gap_concept(slide, left_x, concept_y,
                            col_width, content_height, concepts_to_show[0])
        # Vertical divider in the gutter
        divider_x = left_x + col_width + (gutter / 2) - Pt(2)
        _add_teal_accent_bar(slide, divider_x, concept_y, content_height)
        _render_gap_concept(slide, right_x, concept_y,
                            col_width, content_height, concepts_to_show[1])

    # --- Misconception zone ---
    if misconception.get("wrong") and misconception.get("right"):
        mis_y = Inches(5.5)
        col_width = Inches(5.5)
        gutter = Inches(0.8)
        left_x = MARGIN + Inches(0.3)
        right_x = left_x + col_width + gutter

        # "Common assumption" box (red tint)
        _add_rounded_rect(slide, left_x, mis_y,
                          col_width, Inches(1.05), COLORS["wrong_bg"])
        _add_textbox(slide, left_x + Inches(0.2), mis_y + Inches(0.1),
                     col_width - Inches(0.4), Inches(0.2),
                     "COMMON ASSUMPTION", size=Pt(8),
                     color=COLORS["wrong_text"], bold=True)
        _add_textbox(slide, left_x + Inches(0.2), mis_y + Inches(0.4),
                     col_width - Inches(0.4), Inches(0.55),
                     misconception["wrong"], size=Pt(10),
                     color=COLORS["wrong_text"])

        # "What's actually true" box (green tint)
        _add_rounded_rect(slide, right_x, mis_y,
                          col_width, Inches(1.05), COLORS["right_bg"])
        _add_textbox(slide, right_x + Inches(0.2), mis_y + Inches(0.1),
                     col_width - Inches(0.4), Inches(0.2),
                     "WHAT'S ACTUALLY TRUE", size=Pt(8),
                     color=COLORS["right_text"], bold=True)
        _add_textbox(slide, right_x + Inches(0.2), mis_y + Inches(0.4),
                     col_width - Inches(0.4), Inches(0.55),
                     misconception["right"], size=Pt(10),
                     color=COLORS["right_text"])

    _add_footer(slide)


def _render_gap_concept(slide, x, y, width, height, concept):
    """Render a single concept card within a topic slide.

    Shows: concept name, definition, why it matters, diagram (if any),
    and how it works explanation — with proper vertical spacing.

    Layout budget (within height):
      - Name + badge:   0.35"
      - Definition:     0.45"
      - Why it matters: 0.45" (if present)
      - Diagram:        1.0"  (if present)
      - How it works:   remaining space
    """
    concept_name = concept.get("concept_name", "")
    definition = concept.get("definition", "")
    why_it_matters = concept.get("why_it_matters", "")
    how_it_works = concept.get("how_it_works", "")
    impact = concept.get("impact", "medium")
    diagram_type = concept.get("diagram_type", "none")
    diagram_data = concept.get("diagram_data", {})

    cur_y = y
    bottom_y = y + height  # Hard boundary — nothing below this

    # Concept name — teal bold
    _add_textbox(slide, x, cur_y, width - Inches(1.8), Inches(0.3),
                 concept_name, size=Pt(14), color=COLORS["teal"], bold=True)

    # Relevance badge next to name
    _add_badge(slide, x + width - Inches(1.5), cur_y + Inches(0.02),
               Inches(1.3), Inches(0.25),
               impact.upper(), _impact_color(impact))

    cur_y += Inches(0.35)

    # Definition — charcoal (with right padding)
    _add_textbox(slide, x, cur_y, width - Inches(0.15), Inches(0.4),
                 definition, size=Pt(10), color=COLORS["charcoal"])
    cur_y += Inches(0.45)

    # "Why it matters" callout — gold-tinted box
    if why_it_matters:
        box_h = Inches(0.38)
        box_w = width - Inches(0.1)
        _add_rounded_rect(slide, x, cur_y, box_w, box_h, COLORS["gold_tint"])
        _add_textbox(slide, x + Inches(0.1), cur_y + Inches(0.05),
                     box_w - Inches(0.2), Inches(0.28),
                     f"Why it matters: {why_it_matters}", size=Pt(8),
                     color=COLORS["charcoal"], italic=True)
        cur_y += box_h + Inches(0.1)

    # Diagram (if specified) — use a height proportional to available space
    nodes = diagram_data.get("nodes", [])
    labels = diagram_data.get("labels", [])
    # Reserve space: diagram gets at most 1.0" or half the remaining space
    remaining_for_diagram = bottom_y - cur_y - Inches(0.5)  # leave 0.5" for how_it_works
    diagram_height = min(Inches(1.0), max(remaining_for_diagram * 0.6, Inches(0.6)))

    if diagram_type == "process_flow" and nodes:
        _add_process_flow_diagram(slide, x, cur_y, width, diagram_height, nodes)
        cur_y += diagram_height + Inches(0.1)

    elif diagram_type == "comparison" and (nodes or labels):
        left_items = nodes if nodes else []
        right_items = labels if labels else []
        _add_comparison_diagram(slide, x, cur_y, width, diagram_height,
                                left_items, right_items)
        cur_y += diagram_height + Inches(0.1)

    elif diagram_type == "concept_map" and nodes:
        center = nodes[0] if nodes else concept_name
        satellites = nodes[1:] if len(nodes) > 1 else labels
        _add_concept_map_diagram(slide, x, cur_y, width, diagram_height,
                                 center, satellites)
        cur_y += diagram_height + Inches(0.1)

    # "How it works" explanation — only if space remains and stays within bounds
    remaining = bottom_y - cur_y
    if how_it_works and remaining > Inches(0.25):
        text_h = min(remaining, Inches(0.8))  # Cap text box height
        # Constrain width with inner padding to prevent right-edge overflow
        text_w = width - Inches(0.15)
        # Truncate text if excessively long (slides shouldn't have paragraphs)
        if len(how_it_works) > 250:
            how_it_works = how_it_works[:247] + "..."
        _add_textbox(slide, x, cur_y, text_w, text_h,
                     how_it_works, size=Pt(8), color=COLORS["charcoal"])


def _add_quiz_reflection_slide(prs, topic_data):
    """Quiz / Reflection slide — teal header bar with question + lettered options.

    Design spec: Layout 7 from CR8_Course_PPT_Template_Recommendation.md
    Research: Retrieval practice (Dunlosky et al., 2013) — highest-utility technique.
    """
    quiz = topic_data.get("quiz")
    if not quiz:
        return

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(slide, COLORS["off_white"])

    # --- Teal header bar ---
    bar_height = Inches(0.9)
    _add_rect(slide, Inches(0), Inches(0), SLIDE_WIDTH, bar_height,
              fill_color=COLORS["teal"])
    topic_name = topic_data.get("topic_name", "")
    _add_textbox(slide, MARGIN + Inches(0.2), Inches(0.15), Inches(10), Inches(0.25),
                 f"CHECK YOUR UNDERSTANDING  —  {topic_name}",
                 size=Pt(11), color=COLORS["white"], bold=True)
    _add_textbox(slide, MARGIN + Inches(0.2), Inches(0.45), Inches(10), Inches(0.3),
                 "Test what you've learned", size=Pt(9),
                 color=COLORS["white"], italic=True)

    # --- Question ---
    question = quiz.get("question", "")
    _add_textbox(slide, MARGIN + Inches(0.5), Inches(1.3), Inches(11), Inches(0.8),
                 question, size=Pt(22), color=COLORS["deep_navy"], bold=True,
                 font_family=FONT_TITLE)

    # --- Answer options (A, B, C, D) with teal lettered circles ---
    options = quiz.get("options", [])
    option_letters = ["A", "B", "C", "D"]
    options_y = Inches(2.4)

    for i, option_text in enumerate(options[:4]):
        oy = options_y + i * Inches(0.7)
        letter = option_letters[i]

        # Teal circle with letter
        circle = _add_oval(slide, MARGIN + Inches(0.7), oy + Inches(0.02),
                           Inches(0.4), Inches(0.4), COLORS["teal"])
        tf = circle.text_frame
        tf.word_wrap = False
        p = tf.paragraphs[0]
        p.text = letter
        p.font.size = Pt(14)
        p.font.bold = True
        p.font.color.rgb = COLORS["white"]
        p.font.name = FONT_BODY
        p.alignment = PP_ALIGN.CENTER
        tf.margin_left = Pt(0)
        tf.margin_right = Pt(0)
        tf.margin_top = Pt(0)
        tf.margin_bottom = Pt(0)

        # Clean the option text — remove leading "A) " prefix if present
        clean_text = option_text
        if len(clean_text) > 2 and clean_text[1] in ")].":
            clean_text = clean_text[2:].strip()

        # Option text
        _add_textbox(slide, MARGIN + Inches(1.3), oy, Inches(10), Inches(0.45),
                     clean_text, size=Pt(16), color=COLORS["charcoal"])

    # --- Reflection prompt (italic gold) ---
    reflection = quiz.get("reflection_prompt", "")
    if reflection:
        refl_y = options_y + len(options[:4]) * Inches(0.7) + Inches(0.4)
        _add_rounded_rect(slide, MARGIN + Inches(0.5), refl_y,
                          Inches(11.5), Inches(0.7), COLORS["gold_tint"])
        _add_textbox(slide, MARGIN + Inches(0.8), refl_y + Inches(0.12),
                     Inches(10.5), Inches(0.45),
                     reflection, size=Pt(14),
                     color=COLORS["warm_gold"], italic=True,
                     font_family=FONT_TITLE)

    _add_footer(slide)


def _add_market_intelligence_slide(prs, topic_data):
    """Market Intelligence Spotlight — split layout unique to CR8's value proposition.

    Design spec: Layout 6 from CR8_Course_PPT_Template_Recommendation.md
    Left half: dark navy bg with gold "Market Signal" label + key finding
    Right half: off-white with supporting data/context
    """
    market = topic_data.get("market_signal")
    if not market:
        return

    slide = prs.slides.add_slide(prs.slide_layouts[6])

    # --- Left half: dark navy ---
    half_width = SLIDE_WIDTH / 2
    _add_rect(slide, Inches(0), Inches(0), half_width, SLIDE_HEIGHT,
              fill_color=COLORS["deep_navy"])
    # Right half: off-white
    _add_rect(slide, half_width, Inches(0), half_width, SLIDE_HEIGHT,
              fill_color=COLORS["off_white"])

    # --- Left side content ---
    left_pad = Inches(0.6)
    left_content_w = half_width - Inches(1.2)

    # Gold "MARKET SIGNAL" badge
    _add_badge(slide, left_pad, Inches(1.2), Inches(2.2), Inches(0.4),
               "MARKET SIGNAL", COLORS["warm_gold"])

    # Topic name
    topic_name = topic_data.get("topic_name", "")
    _add_textbox(slide, left_pad, Inches(1.9), left_content_w, Inches(0.4),
                 topic_name, size=Pt(12), color=COLORS["teal"],
                 bold=True)

    # Key finding (large white text)
    signal_text = market.get("signal", "")
    _add_textbox(slide, left_pad, Inches(2.5), left_content_w, Inches(2.0),
                 signal_text, size=Pt(20), color=COLORS["white"], bold=True,
                 font_family=FONT_TITLE)

    # Big stat number (gold, centered)
    stat = market.get("stat", "")
    if stat:
        _add_textbox(slide, left_pad, Inches(4.8), left_content_w, Inches(0.9),
                     stat, size=Pt(52), color=COLORS["warm_gold"], bold=True,
                     font_family=FONT_BODY, alignment=PP_ALIGN.CENTER)
        stat_label = market.get("stat_label", "")
        if stat_label:
            _add_textbox(slide, left_pad, Inches(5.7), left_content_w, Inches(0.4),
                         stat_label, size=Pt(12), color=COLORS["slate_gray"],
                         alignment=PP_ALIGN.CENTER)

    # --- Right side content ---
    right_pad = half_width + Inches(0.6)
    right_content_w = half_width - Inches(1.2)

    # "What This Means For You" header
    _add_textbox(slide, right_pad, Inches(1.2), right_content_w, Inches(0.4),
                 "WHAT THIS MEANS FOR YOU", size=Pt(11),
                 color=COLORS["teal"], bold=True)

    _add_teal_accent_line(slide, right_pad, Inches(1.7), Inches(3))

    # Context / supporting data
    context = market.get("context", "")
    _add_textbox(slide, right_pad, Inches(2.0), right_content_w, Inches(1.8),
                 context, size=Pt(14), color=COLORS["charcoal"])

    # Supporting points (if provided)
    points = market.get("supporting_points", [])
    if points:
        points_y = Inches(4.0)
        _add_textbox(slide, right_pad, points_y - Inches(0.3),
                     right_content_w, Inches(0.25),
                     "KEY EVIDENCE", size=Pt(9), color=COLORS["teal"], bold=True)
        for i, point in enumerate(points[:4]):
            py = points_y + i * Inches(0.45)
            _add_oval(slide, right_pad, py + Inches(0.05),
                      Inches(0.1), Inches(0.1), COLORS["teal"])
            _add_textbox(slide, right_pad + Inches(0.25), py,
                         right_content_w - Inches(0.3), Inches(0.4),
                         point, size=Pt(11), color=COLORS["charcoal"])

    # Source citation at bottom
    source = market.get("source", "")
    if source:
        _add_textbox(slide, right_pad, Inches(6.5), right_content_w, Inches(0.3),
                     f"Source: {source}", size=Pt(8), color=COLORS["slate_gray"],
                     italic=True)

    _add_footer(slide)


def _add_recommendations_slide(prs, slide_data):
    """Recommendations slide — what to learn next."""
    recs = slide_data.get("recommendations_summary", [])
    if not recs:
        return

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(slide, COLORS["off_white"])
    _add_header_bar(slide, "What to Learn Next")

    # Process flow at top: Review → Plan → Practice → Apply
    flow_nodes = ["Review Concepts", "Plan Your Study", "Practice Skills", "Apply in Projects"]
    flow_colors = [COLORS["priority_essential"], COLORS["priority_recommended"],
                   COLORS["teal"], COLORS["priority_supplementary"]]
    _add_process_flow_diagram(slide, MARGIN + Inches(0.5), Inches(1.3),
                              Inches(11.5), Inches(0.8),
                              flow_nodes, flow_colors)

    # Separator
    _add_separator_line(slide, MARGIN + Inches(0.2), Inches(2.3), Inches(12))

    # Sort by priority
    priority_order = {"high": 0, "medium": 1, "low": 2}
    recs_sorted = sorted(recs, key=lambda r: priority_order.get(r.get("priority", "low"), 2))

    y = Inches(2.5)
    for rec in recs_sorted[:8]:
        priority = rec.get("priority", "medium")
        action = rec.get("action", "")
        affected = rec.get("topics_affected", [])

        stripe_color = _impact_color(priority)
        _add_rect(slide, MARGIN + Inches(0.2), y, Inches(0.08), Inches(0.5),
                  fill_color=stripe_color)

        _add_badge(slide, MARGIN + Inches(0.5), y + Inches(0.05),
                   Inches(1.1), Inches(0.35),
                   priority.upper(), stripe_color)

        _add_textbox(slide, Inches(2.3), y, Inches(7), Inches(0.35),
                     action, size=Pt(13), color=COLORS["charcoal"], bold=True)

        if affected:
            topics_text = f"Related topics: {', '.join(affected[:4])}"
            _add_textbox(slide, Inches(2.3), y + Inches(0.35), Inches(7), Inches(0.25),
                         topics_text, size=Pt(9), color=COLORS["slate_gray"], italic=True)

        y += Inches(0.65)

    _add_footer(slide)


def _add_closing_slide(prs, slide_data):
    """Closing slide — Key Takeaways with numbered points."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(slide, COLORS["deep_navy"])

    _add_textbox(slide, MARGIN + Inches(0.5), Inches(0.8), Inches(11), Inches(0.8),
                 "Key Takeaways", size=Pt(36), color=COLORS["warm_gold"],
                 bold=True, font_family=FONT_TITLE, alignment=PP_ALIGN.LEFT)

    _add_teal_accent_line(slide, MARGIN + Inches(0.5), Inches(1.7), Inches(5))

    # Build takeaway points
    takeaways = []
    exec_summary = slide_data.get("executive_summary", {})
    assessment = exec_summary.get("overall_assessment", "")
    if assessment:
        takeaways.append(assessment)

    key_areas = exec_summary.get("critical_gaps", [])
    if key_areas:
        takeaways.append(f"Start with: {key_areas[0]}")

    recs = slide_data.get("recommendations_summary", [])
    high_priority = [r.get("action", "") for r in recs if r.get("priority") == "high"]
    for action in high_priority[:3]:
        takeaways.append(action)

    if not takeaways:
        takeaways = ["Review the concepts covered and practice applying them"]

    y = Inches(2.2)
    for i, point in enumerate(takeaways[:5]):
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

        _add_textbox(slide, MARGIN + Inches(1.1), y, Inches(10.5), Inches(0.4),
                     point, size=Pt(16), color=COLORS["white"])
        y += Inches(0.7)

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

def build_gap_ppt(slide_data: dict, output_path: str) -> tuple[str, dict[str, list[int]]]:
    """Build a Teaching PowerPoint from structured slide data.

    Uses the CR8 "Midnight Teal" design system with these slide types:

    1. Title Slide (Dark)
    2. Course Overview (priority breakdown)
    3. Coverage Radar Chart (your course vs industry)
    4. Topics Overview (scorecard table)
    5. Section Divider (before topic slides)
    6-N. Per-topic groups:
       a. Topic Teaching Slide (assertion-evidence with diagrams)
       b. Market Intelligence Spotlight (industry signal + context)
       c. Quiz / Reflection (retrieval practice)
    N+1. Section Divider (before recommendations)
    N+2. Recommendations (what to learn next)
    N+3. Closing (Key Takeaways)

    Args:
        slide_data: Structured dict produced by ``_structure_slides_parallel``
            (or fallback). Must contain ``presentation_title``,
            ``executive_summary``, ``topic_slides``, and optionally
            ``recommendations_summary``.
        output_path: Filesystem path for the ``.pptx`` file. Parent
            directories are created automatically.

    Returns:
        Tuple of (*output_path*, *topic_slide_map*) where
        *topic_slide_map* maps each topic name to a list of 0-based
        slide indices it occupies in the presentation.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    prs = Presentation()
    prs.slide_width = SLIDE_WIDTH
    prs.slide_height = SLIDE_HEIGHT

    # 1. Title slide
    _add_title_slide(prs, slide_data)

    # 2. Course overview
    _add_executive_summary_slide(prs, slide_data)

    # 3. Radar chart (your course vs industry)
    _add_radar_chart_slide(prs, slide_data)

    # 4. Topics overview
    _add_severity_overview_slide(prs, slide_data)

    # 5. Section divider before topics
    topic_slides = slide_data.get("topic_slides", [])
    if topic_slides:
        _add_section_divider(prs, 1, "Topics & Concepts")

    # 6–N. Per-topic slides: Teaching → Market Intelligence → Quiz
    topic_slide_map: dict[str, list[int]] = {}
    for topic in topic_slides:
        start_idx = len(prs.slides)
        _add_topic_teaching_slide(prs, topic)
        _add_market_intelligence_slide(prs, topic)
        _add_quiz_reflection_slide(prs, topic)
        topic_name = topic.get("topic_name", "Unknown")
        topic_slide_map[topic_name] = list(range(start_idx, len(prs.slides)))

    # N+1. Section divider before recommendations
    recs = slide_data.get("recommendations_summary", [])
    if recs:
        _add_section_divider(prs, 2, "What to Learn Next")

    # N+2. Recommendations
    _add_recommendations_slide(prs, slide_data)

    # N+3. Closing
    _add_closing_slide(prs, slide_data)

    prs.save(output_path)
    return output_path, topic_slide_map
