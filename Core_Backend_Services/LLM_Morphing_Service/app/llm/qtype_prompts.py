"""
app/llm/qtype_prompts.py
─────────────────────────
All ChatPromptTemplates for 5 new question types.
Each type has a set of morph strategy prompts.
"""
from langchain_core.prompts import ChatPromptTemplate

JSON_RULE = "Return ONLY valid JSON. No explanation, no markdown fences."

# ════════════════════════════════════════════════════════════════
#  SHARED: Analyzer prompt (works for all 5 types)
# ════════════════════════════════════════════════════════════════

QTYPE_ANALYZE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", f"""You are an expert exam question analyst.
Analyze the question and return a JSON object with these EXACT keys:
- qtype          : one of [fib, short, msq, numerical, long]
- concept        : core concept being tested (one phrase)
- bloom_level    : one of [remember, understand, apply, analyze, evaluate]
- topic_tags     : list of 2-4 relevant topic strings
- answer_structure: one of [free_text, numeric, multi_select, rubric]
- key_terms      : list of 3-5 important terms from the question
{JSON_RULE}"""),
    ("human", "Section: {section}\nQuestion: {question}\nQuestion Type: {qtype}"),
])

# ════════════════════════════════════════════════════════════════
#  FILL IN THE BLANK
# ════════════════════════════════════════════════════════════════

FIB_REPHRASE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", f"""You are an expert question writer.
Rewrite this fill-in-the-blank question using different sentence structure.
RULES:
1. The blank (________) must still be present — reposition it if needed
2. The correct answer MUST still fill the blank correctly
3. The concept being tested stays the same
4. Return JSON with keys: "question", "correct_answers" (list), "blank_positions" (list of int)
{JSON_RULE}"""),
    ("human", "Question: {question}\nCorrect Answers: {correct_answers}\nConcept: {concept}"),
])

FIB_DIFFICULTY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", f"""You are an expert question writer.
Make this fill-in-the-blank question HARDER by:
- Adding more blanks (convert to multi-blank)
- Requiring a more specific/technical answer
- Removing contextual clues from the sentence
RULES:
1. Keep the same underlying concept
2. Each new blank must have a single clear correct answer
3. Return JSON with keys: "question", "correct_answers" (list, one per blank), "blank_positions" (list)
{JSON_RULE}"""),
    ("human", "Question: {question}\nCorrect Answers: {correct_answers}\nConcept: {concept}\nTarget difficulty: {target_level}"),
])

FIB_CONTEXTUAL_PROMPT = ChatPromptTemplate.from_messages([
    ("system", f"""You are an expert question writer.
Rewrite this fill-in-the-blank question in a completely new context/scenario.
The blank must still test the same factual knowledge.
RULES:
1. Same answer fills the blank
2. Different sentence/scenario framing
3. Return JSON with keys: "question", "correct_answers" (list), "blank_positions" (list)
{JSON_RULE}"""),
    ("human", "Question: {question}\nCorrect Answers: {correct_answers}\nConcept: {concept}"),
])

FIB_MULTBLANK_PROMPT = ChatPromptTemplate.from_messages([
    ("system", f"""You are an expert question writer.
Convert this single-blank question into a multi-blank question (2-3 blanks).
RULES:
1. All blanks test related facts from the same concept
2. Each blank has one clear answer
3. Return JSON: "question" (with multiple ________), "correct_answers" (list, one per blank), "blank_positions" (list)
{JSON_RULE}"""),
    ("human", "Question: {question}\nCorrect Answers: {correct_answers}\nConcept: {concept}"),
])

# ════════════════════════════════════════════════════════════════
#  SHORT ANSWER
# ════════════════════════════════════════════════════════════════

SHORT_REPHRASE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", f"""You are an expert question writer.
Rephrase this short-answer question and update the model answer to match.
RULES:
1. Same concept being tested
2. Update model_answer to fit new phrasing
3. Keep the same keywords list (they are the grading criteria)
4. Return JSON: "question", "model_answer", "keywords" (list)
{JSON_RULE}"""),
    ("human", "Question: {question}\nModel Answer: {model_answer}\nKeywords: {keywords}\nConcept: {concept}"),
])

SHORT_DIFFICULTY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", f"""You are an expert question writer.
Make this short-answer question harder (direction: {{direction}}).
Harder: require more depth, add sub-parts, raise word count minimum.
Easier: reduce scope, lower word count, add guiding structure.
RULES:
1. Update model_answer to match new scope
2. Update keywords and word limits accordingly
3. Return JSON: "question", "model_answer", "keywords" (list), "min_words" (int), "max_words" (int), "explanation"
{JSON_RULE}"""),
    ("human", "Question: {question}\nModel Answer: {model_answer}\nKeywords: {keywords}\nCurrent level: {current_level} → Target: {target_level}\nDirection: {direction}"),
])

SHORT_KEYWORD_SHIFT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", f"""You are an expert question writer.
Keep the question the same but generate a new model answer that emphasizes different keywords.
This creates an alternative grading rubric for the same question.
RULES:
1. Question text: UNCHANGED
2. New model answer covers the concept from a different angle
3. New keywords are different from original (but still valid for the concept)
4. Return JSON: "model_answer", "keywords" (list, all new)
{JSON_RULE}"""),
    ("human", "Question: {question}\nOriginal Model Answer: {model_answer}\nOriginal Keywords: {keywords}\nConcept: {concept}"),
])

SHORT_CONTEXTUAL_PROMPT = ChatPromptTemplate.from_messages([
    ("system", f"""You are an expert question writer.
Rewrite this short-answer question in a new real-world context or application.
The same concept and reasoning are required to answer.
RULES:
1. New scenario/context but same core concept
2. Update model_answer to fit the new context
3. Keep the same keywords (they are grading criteria)
4. Return JSON: "question", "model_answer", "keywords" (list)
{JSON_RULE}"""),
    ("human", "Question: {question}\nModel Answer: {model_answer}\nKeywords: {keywords}\nConcept: {concept}"),
])

# ════════════════════════════════════════════════════════════════
#  MSQ — MULTIPLE SELECT QUESTION
# ════════════════════════════════════════════════════════════════

MSQ_REPHRASE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", f"""You are an expert question writer.
Rephrase this multiple-select question. All options and correct answers stay identical.
RULES:
1. Options list: UNCHANGED
2. Correct answers list: UNCHANGED
3. Only the question text changes
4. Return JSON: "question"
{JSON_RULE}"""),
    ("human", "Question: {question}\nOptions: {options}\nCorrect Answers: {correct_answers}\nConcept: {concept}"),
])

MSQ_DISTRACTOR_PROMPT = ChatPromptTemplate.from_messages([
    ("system", f"""You are an expert question writer.
Replace the WRONG options in this MSQ with more deceptive near-correct distractors.
The correct answers must NOT be touched.
RULES:
1. Correct answers: UNCHANGED — keep them in the new options list
2. Replace wrong options with plausible near-correct alternatives
3. Distractor hardness must match target difficulty and Bloom target:
   - hard/evaluate: subtle, concept-adjacent, common misconceptions
   - medium/apply: plausible but separable with solid understanding
   - easy/remember: clearly wrong but still topic-related
4. Keep total option count the same
5. Return JSON: "options" (full list including correct answers + new wrong options)
{JSON_RULE}"""),
    ("human", "Question: {question}\nOptions: {options}\nCorrect Answers: {correct_answers}\nConcept: {concept}\nCurrent difficulty: {current_level}\nTarget difficulty: {target_level}\nBloom target: {bloom_target}"),
])

MSQ_DIFFICULTY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", f"""You are an expert question writer.
Make this MSQ harder (direction: {{direction}}).
Harder: add 1-2 more correct answers that are subtle/technical, add more options total.
Easier: reduce number of correct answers, make wrong options more obviously wrong.
RULES:
1. All new correct answers must genuinely be correct for the question
2. Regenerate wrong options to match new difficulty
3. Return JSON: "question", "options" (full new list), "correct_answers" (updated list), "explanation"
{JSON_RULE}"""),
    ("human", "Question: {question}\nOptions: {options}\nCorrect Answers: {correct_answers}\nConcept: {concept}\nCurrent level: {current_level} → Target: {target_level}"),
])

MSQ_CONTEXTUAL_PROMPT = ChatPromptTemplate.from_messages([
    ("system", f"""You are an expert question writer.
Rewrite this MSQ with a new real-world scenario while preserving the same core subject.
RULES:
1. Keep the original subject/domain unchanged (example: if the source is about Python, keep it about Python)
2. Keep options UNCHANGED
3. Keep correct_answers UNCHANGED
4. Only rewrite the question stem to add contextual framing
5. Return JSON: "question"
{JSON_RULE}"""),
    ("human", "Question: {question}\nOptions: {options}\nCorrect Answers: {correct_answers}\nConcept: {concept}"),
])

# ════════════════════════════════════════════════════════════════
#  NUMERICAL
# ════════════════════════════════════════════════════════════════

NUMERICAL_REPHRASE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", f"""You are an expert question writer.
Rephrase this numerical question. All numbers and the correct value stay identical.
RULES:
1. Correct value: UNCHANGED
2. Unit: UNCHANGED
3. Only sentence structure changes
4. Return JSON: "question"
{JSON_RULE}"""),
    ("human", "Question: {question}\nCorrect Value: {correct_value} {unit}\nFormula: {formula}\nConcept: {concept}"),
])

NUMERICAL_VALUES_PROMPT = ChatPromptTemplate.from_messages([
    ("system", f"""You are an expert question writer.
Change the input numbers in this numerical question to new values.
Calculate the NEW correct answer using the same formula.
RULES:
1. Use the same formula: {{formula}}
2. New numbers must be realistic for the context
3. Compute the new correct_value mathematically
4. Return JSON: "question", "correct_value" (float), "unit", "explanation" (show the calculation)
{JSON_RULE}"""),
    ("human", "Original Question: {question}\nOriginal Value: {correct_value} {unit}\nFormula: {formula}\nConcept: {concept}"),
])

NUMERICAL_UNITS_PROMPT = ChatPromptTemplate.from_messages([
    ("system", f"""You are an expert question writer.
Convert this numerical question to use different units.
COMMON CONVERSIONS: km↔miles (×0.621), °C↔°F (×9/5+32), kg↔lbs (×2.205), m↔feet (×3.281)
RULES:
1. Convert both the question inputs AND the expected answer to new units
2. Recalculate correct_value in the new unit
3. Round to {{decimal_places}} decimal places
4. Return JSON: "question", "correct_value" (float), "unit" (new unit), "explanation"
{JSON_RULE}"""),
    ("human", "Question: {question}\nCorrect Value: {correct_value} {unit}\nFormula: {formula}\nDecimal places: {decimal_places}"),
])

NUMERICAL_DIFFICULTY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", f"""You are an expert question writer.
Make this numerical question harder by adding calculation steps (direction: {{direction}}).
Harder: add a sub-step (e.g. add a stop, change units mid-problem, two-stage formula).
Easier: give intermediate values, simplify numbers, reduce steps.
RULES:
1. Recalculate the correct_value for the new multi-step problem
2. Show the full calculation in explanation
3. Return JSON: "question", "correct_value" (float), "unit", "formula" (updated), "explanation"
{JSON_RULE}"""),
    ("human", "Question: {question}\nCorrect Value: {correct_value} {unit}\nFormula: {formula}\nCurrent level: {current_level} → Target: {target_level}\nDirection: {direction}"),
])

NUMERICAL_CONTEXTUAL_PROMPT = ChatPromptTemplate.from_messages([
    ("system", f"""You are an expert question writer.
Rewrite this numerical question in a completely different real-world context.
The same formula and calculation structure applies.
RULES:
1. Same formula: {{formula}}
2. Same input values (use same numbers, different physical quantities)
3. Correct answer stays the same
4. Return JSON: "question"
{JSON_RULE}"""),
    ("human", "Question: {question}\nCorrect Value: {correct_value} {unit}\nFormula: {formula}\nConcept: {concept}"),
])

# ════════════════════════════════════════════════════════════════
#  LONG ANSWER
# ════════════════════════════════════════════════════════════════

LONG_REPHRASE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", f"""You are an expert question writer.
Rephrase this long-answer question. The rubric stays completely unchanged.
RULES:
1. Rubric points: UNCHANGED
2. Word limits: UNCHANGED
3. Only the question text is reworded
4. Return JSON: "question"
{JSON_RULE}"""),
    ("human", "Question: {question}\nRubric: {rubric}\nConcept: {concept}"),
])

LONG_CONTEXTUAL_PROMPT = ChatPromptTemplate.from_messages([
    ("system", f"""You are an expert question writer.
Shift this long-answer question to a different time period, geography, or domain.
The rubric analytical framework stays the same — only the context changes.
RULES:
1. Rubric point LABELS may be adapted to new context
2. Rubric marks stay identical
3. Return JSON: "question", "rubric" (updated points with same marks)
{JSON_RULE}"""),
    ("human", "Question: {question}\nRubric: {rubric}\nConcept: {concept}"),
])

LONG_DIFFICULTY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", f"""You are an expert question writer.
Adjust the difficulty of this long-answer question (direction: {{direction}}).
Harder: add rubric points, raise min_areas, increase word minimum, require examples/evidence.
Easier: reduce rubric points, lower min_areas, reduce word limit.
RULES:
1. Recalculate total_marks after adding/removing rubric points
2. Return JSON: "question", "rubric" (full updated rubric), "word_limit" object with integer "min" and "max", "requires_examples" (bool), "explanation"
{JSON_RULE}"""),
    ("human", "Question: {question}\nRubric: {rubric}\nWord Limit: {word_limit}\nCurrent level: {current_level} → Target: {target_level}\nDirection: {direction}"),
])

LONG_FOCUS_SHIFT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", f"""You are an expert question writer.
Keep the same topic but change WHICH aspects the student must discuss.
This changes the rubric points while keeping the same total marks and question domain.
RULES:
1. Total marks: UNCHANGED
2. Number of rubric points: UNCHANGED
3. The specific aspects/points to cover change
4. Return JSON: "question", "rubric" (new points, same total marks)
{JSON_RULE}"""),
    ("human", "Question: {question}\nCurrent Rubric: {rubric}\nConcept: {concept}"),
])

# ════════════════════════════════════════════════════════════════
#  SHARED: Answer verification prompts
# ════════════════════════════════════════════════════════════════

NUMERICAL_VERIFY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", f"""You are a mathematics verifier.
Given this numerical question and claimed answer, verify it is mathematically correct.
Return JSON: "is_correct" (bool), "expected_value" (float), "reason" (one sentence)
{JSON_RULE}"""),
    ("human", "Question: {question}\nFormula: {formula}\nClaimed Answer: {correct_value} {unit}"),
])

SHORT_ANSWER_VERIFY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", f"""You are an expert examiner.
Given this short-answer question and model answer, verify the model answer is accurate and
contains all required keywords.
Return JSON: "is_correct" (bool), "missing_keywords" (list), "reason" (one sentence)
{JSON_RULE}"""),
    ("human", "Question: {question}\nModel Answer: {model_answer}\nRequired Keywords: {keywords}"),
])