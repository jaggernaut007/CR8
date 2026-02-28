"""Rubric prompts for LLM-as-judge evaluation.

Each rubric is a structured prompt that instructs the judge to score
an output on specific criteria with a 1-5 scale.
"""

MODULE_RUBRIC = """You are an expert evaluator of educational content. Score the following learning module on each criterion using a 1-5 scale. Be critical and precise — provide specific textual evidence for each score.

CONTEXT:
- Curriculum scope: {curriculum_scope}
- Topic: {topic_name}
- Gap analysis data: {gap_summary}

MODULE TO EVALUATE:
{output}

Score each criterion independently (do not let one score influence another):

1. DOMAIN_SCOPE_FIDELITY (weight: 0.10)
   Does all content stay within the declared curriculum scope "{curriculum_scope}"?
   5 = Every concept and example is within scope
   3 = Mostly within scope but introduces 1-2 out-of-domain concepts
   1 = Significant scope drift, discusses unrelated technologies

2. GAP_IDENTIFICATION_ACCURACY (weight: 0.15)
   Do the "Identified Gaps" match the gap analysis data provided? Are there fabricated gaps?
   5 = All gaps accurately match the data, priorities are correct
   3 = Most gaps captured but one is missing or fabricated
   1 = Gaps bear little resemblance to the analysis data

3. CURRICULUM_GAP_SEPARATION (weight: 0.10)
   Does "Curriculum Coverage" draw ONLY from curriculum? Does "Core Content" avoid repeating curriculum material?
   5 = Clean separation, no overlap
   3 = Moderate overlap between sections
   1 = Sections are interchangeable

4. PEDAGOGICAL_DEPTH (weight: 0.20)
   Does Core Content teach gap concepts with enough depth to learn standalone (definitions, walkthroughs, examples)?
   5 = Precise definitions, step-by-step walkthroughs, worked examples. Student could learn from this alone.
   3 = Adequate but surface-level. Concepts defined but not deeply taught.
   1 = Bullet-point listing with no real teaching depth.

5. LEARNING_OBJECTIVES_QUALITY (weight: 0.08)
   Do objectives use Bloom's taxonomy verbs, have (Curriculum)/(Gap) tags, include Apply+ level?
   5 = 3-5 objectives, precise Bloom's verbs, properly tagged, measurable, Apply+ present
   3 = Objectives exist with verbs and tags but are generic
   1 = No meaningful objectives

6. INDUSTRY_CONTEXT_RELEVANCE (weight: 0.10)
   Does Industry Context include specific job titles, a detailed use case, grounded skill expectations?
   5 = Specific job titles, concrete use case with details, grounded in research data
   3 = Some specificity but relies on generic statements
   1 = Boilerplate or missing industry context

7. PRACTICE_ASSESSMENT_QUALITY (weight: 0.10)
   Does Quick Check mix formats? Does Apply It create a realistic integration scenario?
   5 = Mixed question types with answers, realistic multi-step scenario
   3 = Questions exist but all same type, or scenario doesn't require gap knowledge
   1 = Practice section is empty or template-quality

8. FACTUAL_GROUNDING (weight: 0.12)
   Are claims traceable to curriculum or research data? Are URLs from the research data?
   5 = All facts traceable to provided data, no fabricated URLs
   3 = Mostly grounded but 2-3 claims from model's general knowledge
   1 = Significant fabrication

9. STRUCTURAL_COMPLETENESS (weight: 0.05)
   Are all 9 required sections present in correct order with proper formatting?
   5 = All sections present, correct order, proper heading hierarchy
   3 = One section missing or out of order
   1 = Unstructured text

Respond in JSON:
{{"scores": [{{"criterion": "<name>", "score": <1-5>, "weight": <float>, "rationale": "<specific evidence>"}}]}}"""


PPT_RUBRIC = """You are an expert evaluator of educational presentations. Score the following PPT slide structure on each criterion using a 1-5 scale.

CONTEXT:
- Curriculum scope: {curriculum_scope}
- Topic: {topic_name}
- Gap analysis data: {gap_summary}

PPT STRUCTURE TO EVALUATE:
{output}

Score each criterion independently:

1. ASSERTION_EVIDENCE_TITLES (weight: 0.15)
   Is each slide_title a complete assertion sentence (subject+verb+predicate, >=5 words)?
   5 = Every title is a full assertion sentence
   3 = Mix of assertions and labels
   1 = All titles are short labels

2. GAP_CONCEPT_TEACHING_DEPTH (weight: 0.25)
   Does each gap_concept have definition, why_it_matters, how_it_works with concrete example, and diagram?
   5 = Each concept has clear definition, specific why, detailed how with example, appropriate diagram
   3 = Definitions present but explanations are generic
   1 = Concepts named only, no real content

3. CURRICULUM_ANCHOR_BREVITY (weight: 0.10)
   Is curriculum_anchor ONE sentence summarizing existing knowledge?
   5 = Exactly one sentence, accurate, serves as launchpad
   3 = 3+ sentences or too vague
   1 = Multi-paragraph or missing

4. SEVERITY_SCORING_ACCURACY (weight: 0.15)
   Are severity ratings consistent with gap data? Do topic_scores reflect real gaps?
   5 = Severity matches gap data, scores show clear gaps for critical topics
   3 = Some inconsistencies between severity and scores
   1 = Severity ratings seem arbitrary

5. DIAGRAM_APPROPRIATENESS (weight: 0.20)
   Is diagram_type appropriate for each concept? Are node labels specific and meaningful?
   5 = All diagram types fit concepts, node labels are specific (2-5 words), most critical gap has a diagram
   3 = Some diagrams don't fit, or labels are generic
   1 = No meaningful diagrams

6. SCHEMA_COMPLIANCE (weight: 0.15)
   Are all required JSON fields present with correct types and nesting?
   5 = Perfect schema compliance
   3 = Valid JSON but 1-2 fields missing
   1 = Invalid or completely wrong structure

Respond in JSON:
{{"scores": [{{"criterion": "<name>", "score": <1-5>, "weight": <float>, "rationale": "<specific evidence>"}}]}}"""


SCRIPT_RUBRIC = """You are an expert evaluator of educational video scripts. Score the following video script on each criterion using a 1-5 scale.

CONTEXT:
- Curriculum scope: {curriculum_scope}
- Topic: {topic_name}
- Gap analysis data: {gap_summary}

SCRIPT TO EVALUATE:
{output}

Score each criterion independently:

1. SIX_SECTION_STRUCTURE (weight: 0.10)
   Are all 6 sections present (Hook, Anchor, Teach-the-Gap, Misconception, Retrieval Prompt, Takeaways) in order, without section labels?
   5 = All 6 sections clearly present, natural transitions, no labels
   3 = 5 of 6 sections present or out of order
   1 = No discernible structure

2. HOOK_EFFECTIVENESS (weight: 0.12)
   Do the first 30-45 words grab attention with a specific hook type (curiosity, scenario, statistic, misconception, value promise)?
   5 = Immediately grabbing, uses clear hook type, specific to topic and gap
   3 = Hook exists but is generic
   1 = Bland opening ("Welcome to this lesson")

3. CURRICULUM_ANCHORING (weight: 0.10)
   Does section 2 reference specific curriculum concepts with anchoring language?
   5 = Explicitly references specific curriculum concepts, clear "you've learned" framing
   3 = Vague anchoring without specific references
   1 = No anchoring, jumps to new material

4. GAP_TEACHING_DEPTH (weight: 0.25)
   Does the core teaching section explain each gap concept with definitions, examples, walkthroughs, and signaling phrases?
   5 = Each gap concept gets definition, industry example, step-by-step walkthrough, signaling phrases, 300-450 words
   3 = Concepts explained but lack depth
   1 = No real teaching, just restates gaps exist

5. SPOKEN_WORD_QUALITY (weight: 0.15)
   Does it sound natural spoken aloud? Conversational "you" language, contractions, no formatting artifacts?
   5 = Perfectly natural spoken language, contractions, direct address, no formatting
   3 = Mix of conversational and written styles
   1 = Clearly written prose, not suitable for speech

6. LENGTH_COMPLIANCE (weight: 0.08)
   Is total length 300-750 words AND under 4500 characters?
   5 = Within both limits
   3 = Slightly outside word range but under char limit
   1 = Extremely short or long

7. MISCONCEPTION_AND_RETRIEVAL (weight: 0.10)
   Does it address a genuine misconception and include a pause-and-think retrieval prompt?
   5 = Specific misconception with correction, genuine retrieval prompt about key concept
   3 = Misconception trivial or retrieval prompt generic
   1 = Missing both

Respond in JSON:
{{"scores": [{{"criterion": "<name>", "score": <1-5>, "weight": <float>, "rationale": "<specific evidence>"}}]}}"""


CONSISTENCY_RUBRIC = """You are an evaluator checking cross-output consistency. Three outputs (module, PPT structure, video script) were generated from the same gap analysis data for the same topic. They should be internally consistent.

TOPIC: {topic_name}
GAP ANALYSIS DATA: {gap_summary}

MODULE:
{module_output}

PPT STRUCTURE:
{ppt_output}

SCRIPT:
{script_output}

Check for consistency across all three outputs:

1. Do the module's "Identified Gaps" match the PPT's gap_concepts?
2. Does the script teach the same concepts as the module's Core Content?
3. Are severity ratings consistent across module and PPT?
4. Do industry examples not contradict each other?
5. Is the curriculum anchor consistent?

Score overall consistency 1-5:
5 = All outputs are fully consistent, teach same concepts, same severity, same examples
3 = Mostly consistent but 1-2 contradictions or missing concepts
1 = Significant contradictions between outputs

Respond in JSON:
{{"scores": [{{"criterion": "CROSS_OUTPUT_CONSISTENCY", "score": <1-5>, "weight": 1.0, "rationale": "<specific contradictions or confirmations>"}}]}}"""
