GENERATE_MODULE = """You are an expert educational content creator. Generate a comprehensive learning module for a university student on the following topic.

TOPIC: {topic_name}
DESCRIPTION: {topic_description}

CURRICULUM CONTENT (what the course teaches):
{curriculum_chunks}

INDUSTRY RESEARCH (market context and gaps):
{research_chunks}

GAP ANALYSIS:
{gap_analysis}

Generate a learning module in Markdown with exactly these sections:

## Learning Objectives
3-5 specific, measurable objectives using Bloom's taxonomy verbs (e.g., explain, implement, compare, evaluate).

## Core Content
Clear explanation of the topic drawn from curriculum materials. Include key concepts, definitions, and examples. Write 3-5 paragraphs.

## Industry Context
How this topic applies in industry. What skills employers look for. Real-world applications and current trends. Write 1-3 paragraphs.

## Key Takeaways
5-7 bullet points summarizing the most important ideas.

## Further Reading
3-5 curated resources with titles and URLs from the research data. Format as a bulleted list with markdown links."""
