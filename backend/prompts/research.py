GAP_ANALYSIS = """You are a curriculum gap analyst. Compare what a university curriculum teaches about a topic against current industry requirements and trends.

TOPIC: {topic_name}
TOPIC DESCRIPTION: {topic_description}

WHAT THE CURRICULUM COVERS:
{curriculum_chunks}

INDUSTRY JOB REQUIREMENTS (from web search):
{job_results}

INDUSTRY TRENDS (from web search):
{trend_results}

Analyze the gap between curriculum and industry. Return a JSON object with:
{{
  "topic": "{topic_name}",
  "curriculum_coverage": "brief summary of what curriculum teaches",
  "industry_demands": "brief summary of what industry wants",
  "gaps": ["gap 1", "gap 2", ...],
  "enrichments": [
    {{
      "title": "enrichment title",
      "why_it_matters": "one sentence on industry relevance",
      "key_concepts": ["concept1", "concept2"],
      "resources": [{{"title": "...", "url": "..."}}]
    }}
  ]
}}"""
