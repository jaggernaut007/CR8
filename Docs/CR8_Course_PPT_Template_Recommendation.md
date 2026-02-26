# CR8 Course PPT Template Recommendation

## Context

CR8's platform programmatically generates educational slide decks from curriculum data enriched with market intelligence. These decks are delivered to **UK university students** (Gen Z, digital-native, enrolled on degree programmes) as part of a multimodal learning pathway alongside AI-generated videos, interactive PDFs, and adaptive quizzes. The template must therefore serve as a **reusable baseline** that PptxGenJS (or python-pptx) can populate at scale — not a one-off design.

---

## Recommended Approach: Custom PptxGenJS Slide Master (Not a Downloaded Template)

**Why not use a pre-made template from Slidesgo, SlidesCarnival, or Canva?**

Downloaded templates are designed for *manual* editing — they rely on drag-and-drop placeholder positioning, decorative illustrations, and fixed layouts that break when populated programmatically. CR8's pipeline generates content dynamically (topic titles, market intelligence data, quiz prompts, charts, key stats), so the template must be built as a **code-first Slide Master system** in PptxGenJS with defined zones, not a visual PPTX file.

That said, the *design language* should be informed by the best patterns in educational template design and grounded in Mayer's multimedia learning principles.

---

## Template Design Specification

### Colour Palette: "Midnight Teal" (CR8-branded)

Given CR8's positioning as an AI-powered curriculum intelligence platform for UK HE, the palette should feel modern, trustworthy, and tech-forward — not generic academic blue.

| Role | Colour | Hex | Usage |
|------|--------|-----|-------|
| **Primary** | Deep Navy | `#0D1B2A` | Dark slide backgrounds, title slides, section dividers |
| **Secondary** | Teal | `#1B998B` | Accent bars, icon circles, data highlights |
| **Tertiary** | Warm Gold | `#F4B942` | Key stat callouts, attention markers, CTA elements |
| **Light base** | Off-White | `#F7F7F2` | Content slide backgrounds |
| **Body text** | Charcoal | `#2D3436` | Body text on light backgrounds |
| **Muted** | Slate Gray | `#636E72` | Captions, source citations, secondary text |
| **White** | White | `#FFFFFF` | Text on dark backgrounds |

This palette gives CR8 a distinctive identity distinct from generic EdTech blue, echoing the "Teal Trust" direction from the PPTX skill guidance while adding warmth through the gold accent.

### Typography

| Element | Font | Size | Weight | Colour |
|---------|------|------|--------|--------|
| Slide title | Georgia | 36–40pt | Bold | White (dark bg) or Deep Navy (light bg) |
| Section header | Calibri | 20–24pt | Bold | Deep Navy or White |
| Body text | Calibri | 14–16pt | Regular | Charcoal `#2D3436` |
| Key stat number | Calibri | 48–60pt | Bold | Teal `#1B998B` or Gold `#F4B942` |
| Stat descriptor | Calibri | 12–14pt | Regular | Slate Gray `#636E72` |
| Source/footer | Calibri | 9–10pt | Regular Italic | Slate Gray `#636E72` |
| Caption/label | Calibri | 10–12pt | Regular | Slate Gray |

Georgia + Calibri is a proven pairing (authority serif headlines with clean sans body) that renders well across all presentation software and supports CR8's position at the intersection of academia and technology.

### Slide Master Layouts (8 types)

These are the reusable Slide Masters that PptxGenJS should define:

#### 1. Title Slide (Dark)
- Full dark navy (`#0D1B2A`) background
- Course title: Georgia 40pt, white, centered upper-third
- Subtitle/module name: Calibri 18pt, teal, centered
- Footer: "Powered by CR8 | [University Name] | [Date]" in 9pt slate
- Optional: subtle teal gradient line across bottom third

#### 2. Section Divider
- Dark navy background
- Large section number: Calibri 72pt bold, gold `#F4B942`, left-aligned
- Section title: Georgia 32pt, white, below number
- Thin teal accent line underneath title

#### 3. Content — Text + Visual (Two-Column)
- Off-white background
- Left column (55%): Title (24pt navy) + body text (14pt charcoal)
- Right column (45%): Placeholder for image, chart, or icon grid
- Teal left-border accent bar (4pt) on the text column
- Source citation in footer zone

#### 4. Key Stats / Data Callout
- Off-white background
- Row of 3–4 metric callouts: big number (48pt teal/gold) with descriptor (12pt slate) below
- Each stat in a subtle light-teal tinted card (`#1B998B` at 8% opacity)
- Section title at top: 24pt navy

#### 5. Content — Full Width
- Off-white background
- Title at top (24pt navy)
- Full-width body area for longer text, embedded charts, or tables
- Teal accent line below title
- Footer with source

#### 6. Market Intelligence Spotlight
- Left half: dark navy background with gold "Market Signal" label + key finding in white text
- Right half: off-white with supporting data, chart, or context in charcoal
- This layout is unique to CR8's value proposition — no off-the-shelf template has this

#### 7. Quiz / Reflection Slide
- Off-white background with teal header bar
- Question in Georgia 24pt
- Answer options in Calibri 16pt with lettered circles (A, B, C, D) in teal
- "Think about it" prompt in italic gold

#### 8. Summary / Takeaway
- Dark navy background
- "Key Takeaways" heading in gold
- 3–5 numbered points in white Calibri 16pt
- Each point prefixed with a teal circle icon
- CR8 branding in footer

### Spacing & Layout Rules

- **Margins**: 0.5" on all sides (minimum)
- **Content blocks**: 0.3" gap between elements
- **Title zone**: Top 15–20% of slide
- **Footer zone**: Bottom 5% (source, page number, branding)
- **Text alignment**: Left-aligned body text (never centered paragraphs)
- **Max bullets per slide**: 5 (prefer 3)
- **Max words per bullet**: 15–20

---

## Alignment with Mayer's Multimedia Learning Principles

| Mayer Principle | How the Template Addresses It |
|-----------------|-------------------------------|
| **Multimedia** | Every content slide includes a visual zone (image, chart, icon) alongside text — no text-only slides |
| **Coherence** | Minimal decorative elements; clean backgrounds; no extraneous animations or clip art |
| **Signaling** | Teal accent bars, gold highlights, and bold stats direct attention to key information |
| **Spatial Contiguity** | Two-column layout places related text and visuals side-by-side on the same slide |
| **Segmenting** | Section dividers break content into discrete modules; quiz slides punctuate learning |
| **Pre-training** | Title slide and section dividers preview what's coming, priming the learner |
| **Redundancy** | Text is concise — slides are designed to complement narration, not duplicate it |
| **Personalization** | Casual, direct language encouraged in content guidelines (second person, conversational) |

---

## Why Not Use an Off-the-Shelf Template

| Concern | Downloaded Template | Custom Slide Master |
|---------|-------------------|-------------------|
| Programmatic population | Breaks layout; placeholders misalign | Built for dynamic content injection |
| Market Intelligence slides | No equivalent layout exists | Custom "Market Signal" layout |
| Quiz/Assessment slides | Not included | Purpose-built with answer options |
| Brand consistency at scale | Varies per template | Enforced via code |
| Accessibility (WCAG 2.1 AA) | Uncontrolled contrast ratios | Palette designed for ≥4.5:1 contrast |
| Mayer's principles | Decorative elements violate coherence | Every element serves a learning function |

---

## Recommended Free Templates as *Design Inspiration* (Not Direct Use)

While the template should be built programmatically, these free resources are worth examining for layout ideas:

1. **Slidesgo "E-Learning" template** — clean two-column layouts, modern sans-serif typography, good use of icon + text rows
2. **SlidesCarnival university templates** — professional, minimal decoration, strong typographic hierarchy
3. **Microsoft Education templates** — accessible colour contrasts, clean grid structures
4. **SlideModel lecture templates** — good examples of timeline, process flow, and chart integration in educational contexts

---

## Implementation Path

1. Define the 8 Slide Masters in PptxGenJS using the spec above
2. Create a `cr8_template.js` config file that maps content types (intro, concept, stat, market_signal, quiz, summary) to the appropriate master
3. Build a thin wrapper that accepts structured JSON (from CR8's content generation agent) and outputs a branded .pptx
4. Run visual QA on the first 3–5 generated decks using the PPTX skill's QA pipeline
5. Iterate on spacing, font sizes, and colour contrast based on rendered output

---

*This specification should serve as the single source of truth for all course PPTs generated by the CR8 platform.*
