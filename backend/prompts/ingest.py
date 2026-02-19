SUMMARIZE_FILE = """You are a curriculum analyst. Summarize the following extracted text from a university course material file. Focus on:
- What topics and concepts are taught
- Key technical terms and methods covered
- The level of depth for each topic

Keep your summary to 300-500 words. Be specific about technical content.

FILE: {source}
TEXT:
{text}"""

EXTRACT_TOPICS = """You are a curriculum analyst. Given the following summaries of university course materials, identify all distinct topics taught in this curriculum.

Return a JSON object with a single key "topics" containing an array of objects, each with:
- "name": short topic name (2-5 words)
- "description": one-sentence description of what this topic covers

Be specific. For example, prefer "Word2Vec Embeddings" over "Word Embeddings".
Extract 10-25 topics. Do not include meta-topics like "Course Overview" or "Final Project".

COURSE SUMMARIES:
{summaries}"""
