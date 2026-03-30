from langchain_core.prompts import ChatPromptTemplate

# ── Analyzer ────────────────────────────────────────────────────────────────

ANALYZE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert exam question analyst.
Analyze the given question and return a JSON object with these exact keys:
- concept: the core concept being tested (e.g. "speed-time-distance")
- formula: the underlying formula or logic (e.g. "time = distance / speed")
- key_values: dict of important numbers extracted (e.g. {{"speed": 60, "distance": 210}})
- bloom_level: one of [remember, understand, apply, analyze, evaluate]
- topic_tags: list of 2-4 relevant topic strings

Return ONLY valid JSON. No explanation, no markdown fences."""),
    ("human", """Section: {section}
Question: {question}
Options: {options}
Correct Answer: {correct_answer}"""),
])

# ── Rephrase ────────────────────────────────────────────────────────────────

REPHRASE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert exam question writer.
Rewrite the given question using completely different vocabulary and sentence structure.

STRICT RULES:
1. Keep all numbers exactly the same
2. Keep the same correct answer
3. Keep all options exactly the same  
4. Do NOT change the mathematical logic or meaning
5. Return ONLY a JSON object with key "question" containing the rewritten question text.
No explanation, no markdown fences."""),
    ("human", """Question: {question}
Options: {options}
Correct Answer: {correct_answer}
Concept: {concept}"""),
])

# ── Contextual ───────────────────────────────────────────────────────────────

CONTEXTUAL_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert exam question writer.
Rewrite the question by placing it in a completely new real-world scenario/domain
while preserving the exact same mathematical logic and values.

STRICT RULES:
1. Use the same numbers: {key_values}
2. The correct answer must still be: {correct_answer}
3. Same options, different context story
4. New domain must NOT be the same as original (no trains if original has trains)
5. Return ONLY a JSON object with key "question". No markdown fences."""),
    ("human", """Original Question: {question}
Options: {options}
Correct Answer: {correct_answer}
Formula/Logic: {formula}
Key Values: {key_values}"""),
])

# ── Distractor ───────────────────────────────────────────────────────────────

DISTRACTOR_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert exam question writer.
Generate {n_distractors} new WRONG answer options (distractors) that will trap students
who make common mistakes.

The correct answer is: {correct_answer}
Concept being tested: {concept}
Formula: {formula}

Generate trap answers based on these common error types:
- Integer/rounding error (e.g. student drops decimals)
- Inverted formula (e.g. uses speed/distance instead of distance/speed)
- Off-by-one or unit confusion
- Plausible but slightly off values

RULES:
1. None of the distractors should equal the correct answer: {correct_answer}
2. All distractors must be plausible (not obviously wrong)
3. Return ONLY a JSON object with key "options" containing a list of ALL options
   (include the correct answer at a random position among the distractors).
No markdown fences."""),
    ("human", """Question: {question}
Correct Answer: {correct_answer}
Original Options: {options}"""),
])

# ── Structural ────────────────────────────────────────────────────────────────

STRUCTURAL_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert exam question writer.
Convert the given MCQ question to the target format: {to_type}

Conversion rules:
- fill_blank: Replace the answer part with "________". Return question text only.
- true_false: Convert to a true/false statement. The correct answer becomes "True" or "False".
- short_answer: Remove all options. Ask as an open question expecting a typed answer.

Return ONLY a JSON object with keys:
- "question": the converted question text
- "correct_answer": the answer in the new format
- "options": list of options (empty list [] for fill_blank and short_answer, ["True","False"] for true_false)
No markdown fences."""),
    ("human", """Question: {question}
Options: {options}
Correct Answer: {correct_answer}
Target Format: {to_type}"""),
])

# ── Difficulty ────────────────────────────────────────────────────────────────

DIFFICULTY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert exam question writer.
Modify the difficulty of the question from level {current_level} to level {target_level} (scale 1-5).

Direction: {direction}

If making HARDER:
- Add an extra calculation step (e.g. a stop, a conversion, a second leg)
- Change round numbers to decimals
- Add a constraint or condition

If making EASIER:
- Remove a step
- Use simpler round numbers
- Add a hint in the question

RULES:
1. The new correct answer will likely CHANGE — calculate it carefully
2. Generate 4 new wrong options (distractors) around the new correct answer
3. Return ONLY a JSON object with keys:
   - "question": modified question text
   - "options": list of 5 options including correct answer
   - "correct_answer": the new correct answer (as it appears in options)
   - "explanation": one sentence explaining what you changed
No markdown fences."""),
    ("human", """Question: {question}
Options: {options}
Correct Answer: {correct_answer}
Concept: {concept}
Formula: {formula}
Key Values: {key_values}
Current Level: {current_level}
Target Level: {target_level}"""),
])

# ── Validator: answer check ───────────────────────────────────────────────────

ANSWER_CHECK_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a math/logic verifier.
Given this question and its claimed correct answer, verify if the answer is mathematically correct.
Return ONLY a JSON object with keys:
- "is_correct": true or false
- "expected_answer": what you calculate the answer to be
- "reason": one sentence explanation
No markdown fences."""),
    ("human", """Question: {question}
Claimed Correct Answer: {correct_answer}
Options: {options}"""),
])