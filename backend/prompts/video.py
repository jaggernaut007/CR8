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
