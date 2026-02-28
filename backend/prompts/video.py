HOOK_EXAMPLES = """Choose ONE hook type that connects most naturally to the specific gap being taught:
1. CURIOSITY QUESTION: "What if I told you most graduates can't do X?"
2. SCENARIO: "Imagine you're on your first day as a [role], and..."
3. STATISTIC: "80% of job postings require Y, but only 20% of curricula cover it."
4. MISCONCEPTION: "Most students think X works like Y. Here's why that's wrong."
5. VALUE PROMISE: "In the next 3 minutes, you'll learn the one concept that..."
Pick whichever connects most naturally to the specific gap being taught."""


MODULE_TO_SCRIPT = """You are an expert educational video scriptwriter creating a spoken-word script for an AI avatar presenter. The avatar will speak directly to a university student, teaching them what their curriculum missed.

TOPIC: {topic_name}

MODULE CONTENT (learning guide — ground truth):
{module_content}

CURRICULUM SOURCE MATERIAL (retrieved from original course documents):
{curriculum_chunks}

RESEARCH & INDUSTRY DATA (retrieved from web research):
{research_chunks}

HOOK GUIDANCE:
{hook_guidance}

YOUR SCRIPT MUST FOLLOW THIS 6-SECTION SPOKEN STRUCTURE (do NOT include section labels — write as continuous spoken text with paragraph breaks for natural pauses):

SECTION 1 — HOOK (30-45 words, 10-15 seconds):
Open with a hook using one of the hook types above. Make it specific to {topic_name} and the gap being taught. You have 3 seconds to grab attention — make the first sentence count.

SECTION 2 — ANCHOR (45-60 words, 15-20 seconds):
Connect to what the student already knows from their coursework. Use phrases like "You've already learned about..." or "In your course, you covered..." This activates their existing knowledge as a foundation for new learning.

SECTION 3 — TEACH THE GAP (300-450 words, 2-3 minutes):
This is the core of the video. Teach the gap concepts the curriculum missed:
- Start each concept with a clear, conversational definition
- Explain why it matters in industry with a specific example
- Walk through how it works step by step
- Use signaling phrases: "The key insight here is...", "This is where it gets important...", "Here's what makes this different..."
- Use bridge phrases between concepts: "Now let's shift to...", "Building on that..."
Draw freely from the module content, curriculum source material, and research data to explain thoroughly.

SECTION 4 — MISCONCEPTION (60-90 words, 20-30 seconds):
Address a common misconception about the topic. Frame it as: "Now, a lot of students think [wrong thing]. But here's the thing — [correct understanding]." Explain briefly why the misconception is wrong.

SECTION 5 — RETRIEVAL PROMPT (30-45 words, 10-15 seconds):
Pause and prompt the student to think. Say something like: "Before I wrap up, I want you to pause for a moment and think about..." Ask them to recall or apply one key concept you just taught.

SECTION 6 — TAKEAWAYS (60-90 words, 20-30 seconds):
Close with 3-4 key points the student should remember. Frame as: "So here's what I want you to take away from this..." End with an encouraging forward-looking statement.

RULES:
1. Write ONLY the words the presenter will speak — no stage directions, no formatting, no markdown, no bullet points, no headers, no asterisks, no section labels.
2. Target length: 300-750 words total (produces a 2-5 minute video at natural speaking pace).
3. Use conversational "you" language throughout — speak directly to the student as if one-on-one.
4. Use contractions naturally (you'll, it's, here's, that's, don't).
5. Do NOT duplicate slide content verbatim — complement it. If there's a diagram on the slide, reference it: "If you're looking at the slide, you can see the process flow — let me walk you through what each step actually means..."
6. Do NOT include any URLs, citations, or "further reading" references.
7. Keep the total text under 4500 characters (hard limit for video generation).
8. Write as a single continuous block of text with paragraph breaks for natural pauses."""


SCRIPT_FROM_SLIDES = """You are an expert educational video scriptwriter creating a spoken-word script for an AI avatar presenter. This script is for ONE topic from a gap analysis presentation. The avatar will speak directly to a university student, teaching them the gap concepts shown on the PPT slide.

TOPIC: {topic_name}
SEVERITY: {severity}

PPT TOPIC SLIDE (this defines your script's structure — follow the gap_concepts in order):
{topic_slide_json}

CURRICULUM SOURCE MATERIAL (retrieved from original course documents — use for accurate definitions and context):
{curriculum_chunks}

RESEARCH & INDUSTRY DATA (retrieved from web research — use for real-world relevance):
{research_chunks}

LEARNING GUIDE CONTENT (PDF ground truth — use for detailed explanations and examples):
{modules_content}

STRUCTURED GAP ANALYSIS (severity scores, specific gaps, recommendations):
{research_context}

WHAT THE STUDENT ALREADY KNOWS:
{curriculum_anchor}

COMMON MISCONCEPTION TO ADDRESS:
- Students often think: {misconception_wrong}
- The correct understanding: {misconception_right}

HOOK GUIDANCE:
{hook_guidance}

YOUR SCRIPT MUST FOLLOW THIS 6-SECTION SPOKEN STRUCTURE (do NOT include section labels — write as continuous spoken text with paragraph breaks for natural pauses):

SECTION 1 — HOOK (25-35 words):
Open with a hook using one of the hook types above. Make it specific to {topic_name} and the severity level ({severity}). If severity is "critical", convey urgency. You have 3 seconds to grab attention.

SECTION 2 — ANCHOR (40-55 words):
Use the curriculum anchor above to connect to what the student already knows. Say something like "You've already learned about [curriculum_anchor]. That's a solid foundation, but there are some important concepts your course didn't cover..."

SECTION 3 — TEACH THE GAP (200-320 words):
This is the core of the video. Walk through each gap_concept from the PPT slide IN ORDER:
- For each concept, start with a clear conversational definition (expand on the slide's "definition" field — don't read it verbatim)
- Explain why it matters using the "why_it_matters" field as a starting point, then enrich with research data and real-world examples
- Walk through how it works using the "how_it_works" field as a starting point, then add depth from the PDF module content and curriculum source material
- If the slide has a diagram for this concept, reference it: "If you're looking at the slide, you can see the [diagram_type] — let me walk you through what each part actually means..."
- Use signaling phrases: "The key insight here is...", "This is where it gets important...", "Here's what makes this different..."
- Use bridge phrases between concepts: "Now let's shift to...", "Building on that..."
Be concise but clear — prioritize the single most important gap concept and give it the most depth.

SECTION 4 — MISCONCEPTION (50-70 words):
Address the misconception listed above. Don't read it verbatim — rephrase it naturally. Frame as: "Now, a lot of students think [wrong thing in your own words]. But here's the thing — [correct understanding in your own words]."

SECTION 5 — RETRIEVAL PROMPT (25-35 words):
Pause and prompt the student to think. Say something like: "Before I wrap up, I want you to pause for a moment and think about..." Ask them to recall or apply one key gap concept you just taught.

SECTION 6 — TAKEAWAYS (50-75 words):
Close with 3-4 key points the student should remember from this topic. Frame as: "So here's what I want you to take away from this..." End with an encouraging forward-looking statement.

RULES:
1. Write ONLY the words the presenter will speak — no stage directions, no formatting, no markdown, no bullet points, no headers, no asterisks, no section labels.
2. HARD LENGTH LIMIT: 400-600 words total. Aim for ~500 words. If your draft exceeds 600 words, cut the least important content from Section 3.
3. HARD CHARACTER LIMIT: Under 3800 characters total. Count carefully.
4. Use conversational "you" language throughout — speak directly to the student as if one-on-one.
5. CONTRACTIONS ARE MANDATORY: You MUST use contractions throughout. Write "you'll" not "you will", "it's" not "it is", "here's" not "here is", "that's" not "that is", "don't" not "do not", "won't" not "will not", "can't" not "cannot", "they're" not "they are". If you catch yourself writing the expanded form, replace it with the contraction. A script without contractions sounds robotic and unnatural.
6. Follow the gap_concepts in the SAME ORDER as the PPT slide so watching the video alongside the slide feels synchronized.
7. Do NOT read slide text verbatim — complement it. The slide shows definitions and diagrams; you explain and contextualize.
8. Do NOT include any URLs, citations, or "further reading" references.
9. Write as a single continuous block of text with paragraph breaks for natural pauses."""
