MODULE_TO_SCRIPT = """You are a professional educational video scriptwriter. Convert the following learning module into a spoken-word video script suitable for an AI avatar presenter.

TOPIC: {topic_name}

MODULE CONTENT (markdown):
{module_content}

RULES:
1. Write ONLY the words the presenter will speak — no stage directions, no formatting, no markdown, no bullet points, no headers, no asterisks.
2. Target length: 300-750 words (produces a 2-5 minute video at natural speaking pace).
3. Use a clear, engaging, educational tone as if lecturing to a university student one-on-one.
4. Structure the script as a natural spoken narrative:
   - Open with a brief hook or context-setting sentence about why {topic_name} matters.
   - Cover the core concepts and key definitions from the curriculum.
   - Highlight the most important industry context and practical relevance.
   - Address the main gaps between what's taught and what industry expects.
   - Close with 3-4 key takeaways the student should remember.
5. Use transitional phrases ("Now, let's look at...", "What's particularly interesting is...", "In practice, this means...") to maintain flow.
6. Avoid jargon dumps — if you introduce a technical term, briefly explain it.
7. Do NOT include any URLs, citations, or "further reading" references — those belong in the written PDF, not a video.
8. Keep the total text under 4500 characters (hard limit for video generation).

Write the script as a single continuous block of text with paragraph breaks for natural pauses."""


SCRIPT_FROM_SLIDES = """You are a professional educational video scriptwriter. Generate a spoken-word narration script that walks through a presentation slide by slide.

You have three sources to draw from:
1. PRESENTATION SLIDES — defines the structure and order of the script
2. LEARNING GUIDE CONTENT — the detailed PDF content for rich, accurate narration
3. RESEARCH & GAP DATA — industry context, gap analysis, and enrichments

PRESENTATION SLIDES (this defines your script structure):
{slide_data_json}

LEARNING GUIDE CONTENT (PDF source — use for detailed explanations):
{modules_content}

RESEARCH & GAP ANALYSIS DATA (use for industry context and gap details):
{research_context}

RULES:
1. Write one clearly labeled section per slide: [SLIDE N: <slide title>]
2. The script STRUCTURE must follow the slides exactly — one section per slide, in order.
3. The script CONTENT should draw from ALL sources:
   - Use the learning guide for detailed explanations, definitions, and examples.
   - Use the research/gap data for industry context and real-world relevance.
   - Use the slide content for the key points to emphasize.
4. For the Title slide: 1-2 sentences introducing the presentation (30-50 words).
5. For the Executive Summary slide: summarize the key findings (80-120 words).
6. For each Topic slide: explain the curriculum coverage, highlight gaps, and give recommendations (100-200 words).
7. For the Recommendations slide: summarize top actions (80-120 words).
8. For the Closing slide: 1-2 sentences wrapping up (20-40 words).
9. Write ONLY spoken words — no stage directions, no markdown, no bullet points, no asterisks.
10. Use a clear, engaging, educational tone as if presenting to university students.
11. Use transitions between slides ("Moving on to...", "Now let's examine...", "Next, we'll look at...").
12. Do NOT include URLs, citations, or "further reading" references.
13. Keep the total script under 4500 characters per topic slide section (hard limit for video generation)."""
