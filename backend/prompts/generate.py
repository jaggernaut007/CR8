GENERATE_MODULE = """You are an expert educational content creator. Generate a focused learning module for a university student on the following topic.

IMPORTANT: This module is part of a curriculum on "{curriculum_scope}". All content must stay within this domain. Do not introduce unrelated technologies or tangential concepts.
IMPORTANT: Do not state anything as fact that is not supported by the CURRICULUM CONTENT or INDUSTRY RESEARCH provided below.
IMPORTANT: Use ### sub-headings within Core Content and Practice & Review to structure the content. Use numbered lists (1., 2., 3.) for sequential steps. Use bullet points (- ) for unordered lists.

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

## Module Overview
Write 3-5 sentences that preview this module. Include:
- A brief real-world problem or scenario that {topic_name} solves (e.g., "Imagine you are building X and encounter Y...")
- Why this topic matters right now in industry
- What the student will gain from this module that goes beyond their coursework
End with a question or hook that motivates reading further. Draw from all sources — CURRICULUM CONTENT, INDUSTRY RESEARCH, and GAP ANALYSIS — to frame relevance.

## Learning Objectives
3-5 specific, measurable objectives using Bloom's taxonomy verbs (e.g., explain, implement, compare, evaluate). Objectives must relate directly to {topic_name}.
IMPORTANT: Include BOTH:
- Objectives for mastering what the curriculum teaches (the techniques listed under KEY TECHNIQUES)
- Objectives for addressing the gaps identified in the GAP ANALYSIS (the skills or knowledge industry demands but the curriculum does not cover)
Include at least one objective at the Apply level or higher. Gap-tagged objectives should target higher Bloom's levels (Apply, Analyze, Evaluate) because they address skills the student needs to build, not just recall.

CRITICAL: Every single objective MUST end with exactly one of these tags: (Curriculum) or (Gap). An objective without a tag is INVALID. You must have at least one of each type.
Example format:
- Explain the skip-gram architecture and its training procedure (Curriculum)
- Implement negative sampling to optimize training on large corpora (Gap)
- Compare CBOW and skip-gram performance trade-offs for production workloads (Gap)

## Curriculum Coverage
Summarize what the original course materials teach about {topic_name}. Specifically address:
- What concepts, definitions, and theory the curriculum covers
- Which techniques are taught: {key_techniques}
- The depth and practical emphasis of the curriculum's treatment
Write 2-3 paragraphs. Draw ONLY from the CURRICULUM CONTENT above — do not add information from research or gap analysis here. This section should give the reader a clear picture of what they already learned from their course.

End with 2-3 quick-check questions to test recall: "Before continuing, make sure you can answer:" followed by brief questions about the key curriculum concepts.

## Identified Gaps
Based on the GAP ANALYSIS above, describe the gaps between what the curriculum teaches and what industry currently demands for {topic_name}. Frame each gap as an opportunity to build valuable skills, not as a deficiency. For each gap:
- State what is missing or underdeveloped in the curriculum
- Explain briefly why this matters for employability or practical competence
- Indicate priority: (Critical), (Important), or (Nice-to-have) based on how frequently this skill appears in industry demands
If the gap analysis lists no gaps, state that the curriculum coverage aligns well with current industry expectations and note any minor areas for deeper exploration. Write 1-3 paragraphs.

## Core Content
This is the main teaching section. Do NOT repeat what the curriculum already teaches — Curriculum Coverage handles that. This section exists to teach the student what they are missing. Focus entirely on closing the knowledge gaps identified above.

### What You Need to Learn
Identify the top 1-2 most critical gaps from the GAP ANALYSIS (the ones most frequently demanded by industry). For each gap, TEACH the concept fully:
- Anchor it to something the student already learned from the curriculum ("Building on [curriculum concept you studied]...")
- Define the concept clearly with a precise definition
- Explain how it works with a detailed walkthrough or worked example
- Walk through application step by step (use numbered steps: 1., 2., 3.)
- Include a concrete example from current industry practice
The student should be able to understand and apply these concepts from this section alone, without needing external resources. Write 3-5 paragraphs per gap concept.

For any remaining lesser gaps, provide a brief summary (1-2 sentences each): what it is, why it matters, and where to learn more (reference the Further Reading section).

Draw from INDUSTRY RESEARCH and GAP ANALYSIS. Do NOT rehash curriculum content — assume the student already knows it.

### Common Misconceptions
List 2-3 things students commonly get wrong about {topic_name}, focusing on misconceptions related to the gap concepts taught above:
- State the misconception
- Explain why it is wrong
- Provide the correct understanding

## Industry Context
How {topic_name} specifically applies in industry. Include:
- 2-3 specific job titles or roles where this skill is valued
- One real-world use case described in detail (company or domain, problem, how {topic_name} is applied, outcome)
- What skills employers look for when hiring for roles that use these specific techniques
Do NOT discuss unrelated industry trends or technologies outside the scope of {topic_name}. Write 2-3 paragraphs.

## Practice & Review

### Quick Check
3-5 retrieval practice questions mixing formats:
- 2 factual recall questions testing concepts from Curriculum Coverage
- 1 conceptual question testing understanding of a gap concept from Core Content
- 1 application question that requires connecting curriculum knowledge to a gap concept
Provide a brief answer after each question (prefix with "> Answer: ").

### Apply It
Design one realistic scenario (4-6 sentences) that requires the student to use both curriculum knowledge and gap-bridging knowledge from Core Content. Then:
- List 3-4 specific tasks the student should complete within the scenario
- Describe the expected outcome or deliverable

## Key Takeaways
7-10 bullet points summarizing the most important ideas about {topic_name}. Structure them as follows:
- First, 3-5 bullet points covering the core curriculum knowledge (prefix each with "Curriculum: ")
- Then, 2-4 bullet points covering gap-related insights and what the student should learn beyond the curriculum (prefix each with "Gap: ")
- Finally, 1-2 bullet points on how curriculum knowledge and gap knowledge connect in practice (prefix each with "Integration: ")

## Reflection
Provide exactly 3 metacognitive prompts to help the student consolidate their learning:
- "What was the most important thing you learned in this module?"
- "Which gap area do you feel least confident about? What would help you strengthen it?"
- "How does {topic_name} connect to other topics you have studied?"

## Further Reading
3-5 curated resources with titles and URLs from the INDUSTRY RESEARCH data. Only include resources directly relevant to {topic_name}. Do NOT fabricate URLs — only use URLs that appear in the INDUSTRY RESEARCH above.
For each resource, include:
- The title as a markdown link
- Type in parentheses: (Tutorial), (Documentation), (Research Paper), or (Video)
- Difficulty level: (Beginner), (Intermediate), or (Advanced)
- One sentence describing what the student will gain from it
Format as a bulleted list."""
