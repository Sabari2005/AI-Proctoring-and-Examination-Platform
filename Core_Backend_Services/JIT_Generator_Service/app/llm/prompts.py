"""
JIT/app/llm/prompts.py
───────────────────────
All prompts for JIT: question generation (per type) + answer evaluation.
"""
from langchain_core.prompts import ChatPromptTemplate

J = "Return ONLY valid JSON. No markdown fences, no explanation."

# ════════════════════════════════════════════════════════════════
#  SUB-TOPIC EXTRACTION
# ════════════════════════════════════════════════════════════════

SUBTOPIC_PROMPT = ChatPromptTemplate.from_messages([
    ("system", f"""You are a domain expert content planner.
Given a section topic, generate a list of 8-12 specific sub-topics that comprehensively cover it.
Sub-topics must stay strictly inside the given section topic domain.
Return JSON object with key: sub_topics (list of strings)
{J}"""),
    ("human", "Section topic: {section_topic}"),
])

# ════════════════════════════════════════════════════════════════
#  QUESTION GENERATION — one prompt per type
# ════════════════════════════════════════════════════════════════

MCQ_GEN_PROMPT = ChatPromptTemplate.from_messages([
    ("system", f"""You are an expert exam question writer.
Generate ONE high-quality MCQ on the given topic at the specified difficulty.

Difficulty {{difficulty}}/5 (1=very easy, 5=very hard)
Bloom level: {{bloom_level}}

RULES:
1. Question must clearly test the sub-topic at the correct difficulty
2. Exactly 4 options — one clearly correct, three plausible distractors
3. For difficulty 4-5: make distractors subtle and trap-based
4. expected_time_seconds: realistic time for this difficulty (30-120)
5. Return JSON object with keys:
question_text, options, correct_answers, explanation, expected_time_seconds, hints
{J}"""),
    ("human", "Section: {section_topic}\nSub-topic: {sub_topic}\nDifficulty: {difficulty}/5\nBloom: {bloom_level}\nAvoid repeating these questions: {seen_questions}"),
])

FIB_GEN_PROMPT = ChatPromptTemplate.from_messages([
    ("system", f"""You are an expert exam question writer.
Generate ONE fill-in-the-blank question on the given topic at the specified difficulty.

Use ________ as the blank marker. For difficulty 3+: use 2 blanks.
Difficulty {{difficulty}}/5 | Bloom: {{bloom_level}}

Return JSON:
question_text, correct_answers, blank_count, answer_tolerance, explanation, expected_time_seconds
{J}"""),
    ("human", "Section: {section_topic}\nSub-topic: {sub_topic}\nDifficulty: {difficulty}/5\nBloom: {bloom_level}\nAvoid: {seen_questions}"),
])

SHORT_GEN_PROMPT = ChatPromptTemplate.from_messages([
    ("system", f"""You are an expert exam question writer.
Generate ONE short-answer question on the given topic at the specified difficulty.

Difficulty {{difficulty}}/5 | Bloom: {{bloom_level}}
Word limit: difficulty 1-2 → 20-40 words, difficulty 3 → 40-80 words, difficulty 4-5 → 60-120 words.

Return JSON:
question_text, model_answer, keywords, min_words, max_words, explanation, expected_time_seconds
{J}"""),
    ("human", "Section: {section_topic}\nSub-topic: {sub_topic}\nDifficulty: {difficulty}/5\nBloom: {bloom_level}\nAvoid: {seen_questions}"),
])

MSQ_GEN_PROMPT = ChatPromptTemplate.from_messages([
    ("system", f"""You are an expert exam question writer.
Generate ONE multiple-select question (MSQ) — student must select ALL correct answers.

Difficulty {{difficulty}}/5 | Bloom: {{bloom_level}}
Options: 5-6 total, 2-4 correct answers.

Return JSON:
question_text, options, correct_answers, explanation, expected_time_seconds
{J}"""),
    ("human", "Section: {section_topic}\nSub-topic: {sub_topic}\nDifficulty: {difficulty}/5\nBloom: {bloom_level}\nAvoid: {seen_questions}"),
])

NUMERICAL_GEN_PROMPT = ChatPromptTemplate.from_messages([
    ("system", f"""You are an expert exam question writer.
Generate ONE numerical/calculation question on the given topic.

Difficulty {{difficulty}}/5 | Bloom: {{bloom_level}}
- Difficulty 1-2: single formula, round numbers
- Difficulty 3: two-step calculation
- Difficulty 4-5: multi-step, unit conversion, or optimization

Return JSON:
question_text, correct_value, unit, tolerance, formula, explanation, expected_time_seconds
{J}"""),
    ("human", "Section: {section_topic}\nSub-topic: {sub_topic}\nDifficulty: {difficulty}/5\nBloom: {bloom_level}\nAvoid: {seen_questions}"),
])

LONG_GEN_PROMPT = ChatPromptTemplate.from_messages([
    ("system", f"""You are an expert exam question writer.
Generate ONE long-answer/essay question with a marking rubric.

Difficulty {{difficulty}}/5 | Bloom: {{bloom_level}}
- Word limit: difficulty 3 → 200-400 words, difficulty 4 → 300-600 words, difficulty 5 → 400-800 words
- Rubric: 3-5 marking points, each with marks (total = 100)

Return JSON:
question_text, rubric(points,total_marks,min_areas), word_limit(min,max), requires_examples, explanation, expected_time_seconds
{J}"""),
    ("human", "Section: {section_topic}\nSub-topic: {sub_topic}\nDifficulty: {difficulty}/5\nBloom: {bloom_level}\nAvoid: {seen_questions}"),
])

CODING_GEN_PROMPT = ChatPromptTemplate.from_messages([
    ("system", f"""You are an expert competitive programming question writer.
Generate ONE coding problem with test cases.

Difficulty {{difficulty}}/5 | Bloom: {{bloom_level}}
- Difficulty 1-2: simple loops/arrays
- Difficulty 3: hash maps, sorting, basic recursion
- Difficulty 4: trees, graphs, dynamic programming basics
- Difficulty 5: advanced graph algorithms, optimization

**CRITICAL**: Each test case MUST have BOTH 'input' and 'output' fields populated.
- 'input': test input (use JSON string for complex structures, e.g. "[1,2,3]")
- 'output': exact expected output value/string (MUST NOT be empty)
- 'category': one of basic, edge, performance

Use `test_cases` as an object keyed like tc_1, tc_2, tc_3.
Each test case value must include input, output, and category.

Return JSON:
question_text, function_signature, test_cases, constraints, explanation, expected_time_seconds
{J}"""),
    ("human", "Section: {section_topic}\nSub-topic: {sub_topic}\nDifficulty: {difficulty}/5\nBloom: {bloom_level}\nAvoid: {seen_questions}"),
])

# ════════════════════════════════════════════════════════════════
#  ANSWER EVALUATION PROMPTS
# ════════════════════════════════════════════════════════════════

SHORT_EVAL_PROMPT = ChatPromptTemplate.from_messages([
    ("system", f"""You are an expert examiner grading a short-answer response.
Grade the student's answer against the model answer and keywords.

Scoring: 1.0 = fully correct | 0.5 = partially correct | 0.0 = incorrect

Return JSON:
score, status, matched_keywords, missing_keywords, feedback
{J}"""),
    ("human", "Question: {question}\nModel Answer: {model_answer}\nKeywords required: {keywords}\nStudent Answer: {student_answer}"),
])

LONG_EVAL_PROMPT = ChatPromptTemplate.from_messages([
    ("system", f"""You are an expert examiner grading a long-answer essay.
Grade against the rubric. Award marks per rubric point based on coverage.

Return JSON:
total_score, status, rubric_scores(list of point/awarded/max), feedback
{J}"""),
    ("human", "Question: {question}\nRubric: {rubric}\nStudent Answer: {student_answer}"),
])

CODING_EVAL_PROMPT = ChatPromptTemplate.from_messages([
    ("system", f"""You are an expert programmer evaluating a coding solution.
Check the solution against the test cases and problem constraints.

Do not solve or rewrite the student's problem. Your job is only to grade.
Never return source code.

Return JSON:
score, status, tc_passed, tc_total, time_complexity_ok, feedback
{J}"""),
    ("human", "Question: {question}\nTest Cases: {test_cases}\nConstraints: {constraints}\nStudent Code: {student_answer}"),
])


CODING_EVAL_RETRY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", f"""You are a strict JSON grader for coding answers.
Grade the submitted code against the given test cases and constraints.

Hard rules:
1. Output ONLY one JSON object.
2. Do NOT include markdown fences.
3. Do NOT include code.
4. Ensure score is a number between 0.0 and 1.0.

Return JSON keys exactly:
score, status, tc_passed, tc_total, time_complexity_ok, feedback
{J}"""),
    ("human", "Question: {question}\nTest Cases: {test_cases}\nConstraints: {constraints}\nStudent Code: {student_answer}\nPrevious invalid model output: {invalid_output}"),
])

# ════════════════════════════════════════════════════════════════
#  FINAL REPORT GENERATION
# ════════════════════════════════════════════════════════════════

REPORT_GEN_PROMPT = ChatPromptTemplate.from_messages([
    ("system", f"""You are an expert learning assessment analyst.
Generate a detailed adaptive assessment report.

Return JSON:
strengths, weaknesses, recommendations, summary
{J}"""),
    ("human", """Section: {section_topic}
Total questions: {total_questions}
Accuracy: {accuracy}%
Theta: {theta} ({skill_label})
Sub-topic mastery: {subtopic_mastery}
Difficulty trajectory: {trajectory}
Speed profile: {speed_profile}"""),
])