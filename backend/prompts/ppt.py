STRUCTURE_GAP_SLIDES = """You are an expert presentation designer. Create a structured PowerPoint presentation plan from the learning guide content and gap analysis data below.

CURRICULUM SCOPE: {curriculum_scope}
NUMBER OF TOPICS: {topic_count}

LEARNING GUIDE CONTENT (PDF source — this is the ground truth):
{modules_content}

GAP ANALYSIS & RESEARCH DATA:
{gap_summary_json}

Your task: Build a presentation that is **structured around the PDF chapters** (one topic slide per module, in the same order), enriched with gap analysis and research insights. The slides should highlight gaps but also reference the curriculum content from the PDF so the audience understands context.

Return a JSON object with this exact structure:
{{
  "presentation_title": "Gap Analysis: [concise title based on curriculum scope]",
  "executive_summary": {{
    "total_gaps_found": <integer>,
    "critical_gaps": ["gap 1 summary (max 12 words)", ...],
    "overall_assessment": "2-3 sentence assessment of curriculum-industry alignment"
  }},
  "topic_slides": [
    {{
      "topic_name": "...",
      "slide_title": "concise slide title (max 8 words)",
      "severity": "critical" | "moderate" | "minor",
      "curriculum_summary": "1-2 sentences summarizing what the PDF module covers for this topic",
      "industry_summary": "1 sentence on what industry expects (from research data)",
      "gaps": [
        {{
          "gap_title": "short gap name (3-6 words)",
          "description": "1-2 sentences explaining the gap",
          "impact": "high" | "medium" | "low"
        }}
      ],
      "top_recommendations": ["recommendation 1 (max 15 words)", "recommendation 2", ...]
    }}
  ],
  "recommendations_summary": [
    {{
      "priority": "high" | "medium" | "low",
      "action": "specific recommendation (max 20 words)",
      "topics_affected": ["topic1", "topic2"]
    }}
  ]
}}

RULES:
1. Keep all text concise — this is for slides, not a report.
2. **topic_slides must follow the same order as the PDF chapters.** One slide per topic/module.
3. curriculum_summary must accurately reflect the PDF module content for that topic — do not invent information.
4. Severity ratings: "critical" = major industry skill missing, "moderate" = partial coverage needs enhancement, "minor" = small gap or nice-to-have.
5. Limit to 3-5 gaps per topic. If a topic has no gaps, set severity to "minor" and note good alignment.
6. Generate 3-8 prioritized recommendations in recommendations_summary.
7. Every gap must have an impact rating.
"""
