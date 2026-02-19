GENERATE_MODULE = """You are an expert educational content creator. Generate a focused learning module for a university student on the following topic.

IMPORTANT: This module is part of a curriculum on "{curriculum_scope}". All content must stay within this domain. Do not introduce unrelated technologies or tangential concepts.

TOPIC: {topic_name}
DESCRIPTION: {topic_description}
KEY TECHNIQUES FROM CURRICULUM: {key_techniques}

CURRICULUM CONTENT (what the course teaches):
{curriculum_chunks}

INDUSTRY RESEARCH (relevant market context):
{research_chunks}

GAP ANALYSIS:
{gap_analysis}

Generate a learning module in Markdown with exactly these sections, in this order:

## Curriculum Coverage
Summarize what the original course materials teach about {topic_name}. Specifically address:
- What concepts, definitions, and theory the curriculum covers
- Which techniques are taught: {key_techniques}
- The depth and practical emphasis of the curriculum's treatment
Write 2-3 paragraphs. Draw ONLY from the CURRICULUM CONTENT above — do not add information from research or gap analysis here. This section should give the reader a clear picture of what they already learned from their course.

## Identified Gaps
Based on the GAP ANALYSIS above, describe the gaps between what the curriculum teaches and what industry currently demands for {topic_name}. For each gap:
- State what is missing or underdeveloped in the curriculum
- Explain briefly why this matters for employability or practical competence
If the gap analysis lists no gaps, state that the curriculum coverage aligns well with current industry expectations and note any minor areas for deeper exploration. Write 1-3 paragraphs.

## Learning Objectives
3-5 specific, measurable objectives using Bloom's taxonomy verbs (e.g., explain, implement, compare, evaluate). Objectives must relate directly to {topic_name}.
IMPORTANT: Include BOTH:
- Objectives for mastering what the curriculum teaches (the techniques in Curriculum Coverage)
- Objectives for addressing the gaps identified above (the skills or knowledge in Identified Gaps)
Label each objective with a parenthetical tag: (Curriculum) or (Gap) to indicate its source.

## Core Content
Clear explanation of the topic drawn from curriculum materials. Include key concepts, definitions, and examples. Write 3-5 paragraphs.

## Industry Context
How {topic_name} specifically applies in industry. What skills employers look for when hiring for roles that use these specific techniques. Do NOT discuss unrelated industry trends or technologies outside the scope of {topic_name}. Write 1-3 paragraphs.

## Key Takeaways
7-10 bullet points summarizing the most important ideas about {topic_name}. Structure them as follows:
- First, 3-5 bullet points covering the core curriculum knowledge (prefix each with "Curriculum: ")
- Then, 2-4 bullet points covering gap-related insights and what the student should learn beyond the curriculum (prefix each with "Gap: ")
- Finally, 1-2 bullet points on how curriculum knowledge and gap knowledge connect in practice (prefix each with "Integration: ")

## Further Reading
3-5 curated resources with titles and URLs from the research data. Only include resources directly relevant to {topic_name}. Format as a bulleted list with markdown links."""
