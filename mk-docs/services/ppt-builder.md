# PPT Builder

**File**: `backend/services/ppt_builder.py`

Generates professional widescreen (16:9) PowerPoint presentations using `python-pptx` + `matplotlib`. The PPT teaches industry-relevant concepts as a seamless add-on to an existing curriculum, using assertion-evidence slide design grounded in Mayer's multimedia learning principles.

## Public API

```python
def build_gap_ppt(
    slide_data: dict,     # Structured JSON from LLM (see PPT prompt output schema)
    output_path: str,     # Output file path
) -> str                  # Returns output_path
```

## Design System

### Layout

| Element | Value |
|---------|-------|
| Slide dimensions | 13.333" x 7.5" (widescreen 16:9) |
| Heading font | Georgia (serif) |
| Body font | Calibri (sans) |
| Margins | 0.5" all sides |
| Library | python-pptx, matplotlib, numpy |

### Color Palette

| Token | Hex | Usage |
|-------|-----|-------|
| Deep Navy | `#0D1B2A` | Dark backgrounds, headers |
| Teal | `#1B998B` | Accents, badges, diagrams |
| Warm Gold | `#F4B942` | Callouts, stats, section numbers |
| Off White | `#F7F7F2` | Content slide backgrounds |
| Charcoal | `#2D3436` | Body text |
| Slate Gray | `#636E72` | Captions, footers |
| Teal Tint | `#E6F5F3` | Light teal backgrounds for cards |
| Gold Tint | `#FEF6E2` | Light gold backgrounds for callouts |

### Severity Mapping

| Internal Severity | User-Facing Label | Color |
|---|---|---|
| `critical` | ESSENTIAL | Teal |
| `moderate` | RECOMMENDED | Gold |
| `minor` | SUPPLEMENTARY | Slate Gray |

## Slide Sequence

The presentation follows this fixed structure:

| # | Slide Type | Background | Key Elements |
|---|------------|------------|-------------|
| 1 | **Title Slide** | Deep Navy | Georgia 40pt white title, teal accent line, CR8 branding |
| 2 | **Course Overview** | Off White | 5 KPI stat cards (Concepts, Topics, Essential, Recommended, Supplementary), "What You'll Learn" section, key topics list |
| 3 | **Coverage Radar Chart** | Off White | Matplotlib polar chart: teal "Your Course" vs gold "Industry Standard", auto-generated from topic_scores |
| 4 | **Topics at a Glance** | Off White | Scorecard table with topic names, colored severity badges, concept counts; paginated (10 per slide) |
| 5 | **Section Divider** | Deep Navy | Gold section number (72pt), Georgia white title (32pt), teal accent line |
| 6-N | **Per-Topic Group** (3 slides each): | | |
| | a. Topic Teaching | Off White | Assertion title (Georgia 24pt), importance badge, curriculum anchor (italic), concept cards with diagrams, misconception wrong/right boxes |
| | b. Market Intelligence | Split (Navy/Off White) | Left: gold "MARKET SIGNAL" badge, key finding (Georgia 20pt white), stat number (52pt gold); Right: "What This Means For You", context, evidence points, source citation |
| | c. Quiz / Reflection | Off White | Teal header bar, question (Georgia 22pt), A-D options with teal circles, gold reflection prompt |
| N+1 | **Section Divider** | Deep Navy | Section 2: "What to Learn Next" |
| N+2 | **Recommendations** | Off White | Process flow diagram (Review -> Plan -> Practice -> Apply), prioritized recommendation cards with colored stripes |
| N+3 | **Closing** | Deep Navy | "Key Takeaways" (gold Georgia 36pt), numbered points with teal circles |

## Diagram Renderers

Three native diagram types, all built with `python-pptx` shapes (no external images):

### Process Flow (`_add_process_flow_diagram`)

- Left-to-right sequence of rounded rectangles connected by right-arrow shapes
- Teal fill with white bold 9pt text, slate gray arrows
- Adapts node width based on count and available space
- Configurable node colors via `node_colors` parameter

### Comparison (`_add_comparison_diagram`)

- Two-column layout: "Curriculum" (slate gray header) vs "Industry" (teal header)
- Items listed below each header, capped at 4 items
- Adaptive row spacing based on available height

### Concept Map (`_add_concept_map_diagram`)

- Tree diagram: center node (deep navy) with trunk, spine, branch, and satellite nodes (teal)
- Uses horizontal trunk from center to vertical spine, then branches to each satellite
- Satellites stacked vertically, capped at 5
- All connectors are teal 2pt rectangles (not native lines)

## Radar Chart (`_generate_radar_chart`)

- Matplotlib polar plot comparing `curriculum_score` vs `industry_requirement` per topic
- Teal filled polygon for "Your Course", gold for "Industry Standard"
- Labels truncated at 18 characters
- Transparent background, 150dpi PNG embedded via `slide.shapes.add_picture()`
