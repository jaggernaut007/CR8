"""Quiz generation prompt for the CR8 Quiz Agent.

Defines the prompt template used by agent_quiz.py to generate
structured MCQ questions from completed pipeline output.
"""

QUIZ_GENERATE_PROMPT = """You are an expert educational assessment designer. Generate multiple-choice quiz questions to test a university student's understanding of the following topic.

IMPORTANT: This quiz is part of a curriculum on "{curriculum_scope}". All questions must stay within this domain.
IMPORTANT: At least 40% of questions MUST target identified knowledge gaps from the GAP ANALYSIS below.
IMPORTANT: Follow this difficulty distribution exactly:
- 30% Easy (Bloom's: Remember, Understand)
- 50% Medium (Bloom's: Apply, Analyze)
- 20% Hard (Bloom's: Evaluate, Create)

TOPIC: {topic_name}

MODULE CONTENT (what the student studied):
{module_content}

GAP ANALYSIS (skills industry demands but curriculum does not fully cover):
{gap_analysis}

Generate exactly {question_count} multiple-choice questions. Return valid JSON with this exact schema:

{{
  "questions": [
    {{
      "question_text": "Clear, specific question testing one concept",
      "question_type": "mcq",
      "options": ["Option A text", "Option B text", "Option C text", "Option D text"],
      "correct_index": 0,
      "difficulty": "easy",
      "blooms_level": "remember",
      "source_section": "Module section this question tests",
      "feedback_correct": "Brief explanation of why this is correct",
      "feedback_incorrect": "Brief explanation of the correct answer and why",
      "topic": "{topic_name}"
    }}
  ]
}}

RULES:
1. Each question MUST have exactly 4 options (A, B, C, D).
2. correct_index is 0-based (0 = first option, 3 = last option).
3. Options must be plausible and similar in length and style — no obviously wrong answers.
4. difficulty must be one of: "easy", "medium", "hard".
5. blooms_level must be one of: "remember", "understand", "apply", "analyze", "evaluate", "create".
6. Easy questions test recall and comprehension. Medium questions require application or analysis. Hard questions require evaluation or synthesis.
7. Gap-targeting questions should reference skills or concepts from the GAP ANALYSIS, not just the module content.
8. source_section should reference the specific part of the module content the question tests.
9. feedback_correct and feedback_incorrect must be educational — explain the concept, not just state right/wrong.
10. Do NOT repeat questions or test the same concept twice.
"""
