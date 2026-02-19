SUMMARIZE_FILE = """You are a curriculum analyst. Summarize the following extracted text from a university course material file. Focus on:
- What topics and concepts are taught
- Key technical terms and methods covered
- The level of depth for each topic

Keep your summary to 300-500 words. Be specific about technical content.

FILE: {source}
TEXT:
{text}"""

EXTRACT_TOPICS = """You are a curriculum analyst. Given the following summaries of university course materials, identify all distinct topics taught in this curriculum.

IMPORTANT: Your analysis must stay strictly within what the source material actually covers. Do not infer or add topics that are not explicitly present in the summaries.

First, determine the overall scope of this curriculum in one sentence.

Then extract each topic with:
- "name": short topic name (2-5 words)
- "description": one-sentence description of what this topic covers IN THE SOURCE MATERIAL
- "key_techniques": list of 3-8 specific techniques, algorithms, methods, or tools that the source material mentions for this topic
- "domain_context": the broader subject area this topic belongs to, as framed in the source material (e.g., "word vector representations in NLP" not just "NLP")

Return a JSON object:
{{
  "curriculum_scope": "one sentence describing the overall domain and boundaries of this curriculum",
  "topics": [
    {{
      "name": "...",
      "description": "...",
      "key_techniques": ["...", "..."],
      "domain_context": "..."
    }}
  ]
}}

Be specific. For example, prefer "Word2Vec Embeddings" over "Word Embeddings".
Only include techniques that appear in the source material.
Extract 10-25 topics. Do not include meta-topics like "Course Overview" or "Final Project".

COURSE SUMMARIES:
{summaries}"""
