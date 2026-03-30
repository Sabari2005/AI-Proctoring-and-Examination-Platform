"""
JIT/app/nodes/question_generator.py
─────────────────────────────────────
Generates a single fresh question at the current difficulty + sub-topic.
Supports all 7 question types. Uses MIXED rotation if type=mixed.
"""
import random
from langchain_core.messages import HumanMessage
from app.core.state import JITGraphState
from app.core.schemas import GeneratedQuestion
from app.core.enums import QType, DifficultyLevel, DIFFICULTY_TO_BLOOM
from app.llm.providers import invoke_with_fallback
from app.llm.prompts import (
    MCQ_GEN_PROMPT, FIB_GEN_PROMPT, SHORT_GEN_PROMPT, MSQ_GEN_PROMPT,
    NUMERICAL_GEN_PROMPT, LONG_GEN_PROMPT, CODING_GEN_PROMPT,
)
from app.utils.json_parser import parse_llm_json
from app.utils.session_store import new_question_id
from app.core.config import settings

PROMPT_MAP = {
    QType.MCQ:       MCQ_GEN_PROMPT,
    QType.FIB:       FIB_GEN_PROMPT,
    QType.SHORT:     SHORT_GEN_PROMPT,
    QType.MSQ:       MSQ_GEN_PROMPT,
    QType.NUMERICAL: NUMERICAL_GEN_PROMPT,
    QType.LONG:      LONG_GEN_PROMPT,
    QType.CODING:    CODING_GEN_PROMPT,
}

MIXED_ROTATION = [
    QType.MCQ, QType.SHORT, QType.MCQ, QType.FIB,
    QType.MSQ, QType.NUMERICAL, QType.MCQ, QType.SHORT,
]


def _fallback_question_payload(
    qtype: QType,
    section_topic: str,
    sub_topic: str,
    difficulty: DifficultyLevel,
    bloom: str,
) -> dict:
    stem = f"[{section_topic}] {sub_topic} ({bloom}, level {difficulty.value})"

    if qtype == QType.MCQ:
        return {
            "question_text": f"Which statement best describes the topic: {stem}?",
            "options": [
                f"A. {sub_topic} focuses on organizing and accessing data.",
                "B. It is only used for UI design.",
                "C. It cannot be used in programming.",
                "D. It is unrelated to algorithms.",
            ],
            "correct_answers": [f"A. {sub_topic} focuses on organizing and accessing data."],
            "explanation": "Fallback MCQ generated due to malformed LLM JSON.",
            "expected_time_seconds": settings.EXPECTED_TIMES.get("mcq", 60),
            "hints": [f"Think about the purpose of {sub_topic} in {section_topic}."],
        }

    if qtype == QType.FIB:
        return {
            "question_text": f"In {section_topic}, {sub_topic} is used to ________.",
            "correct_answers": ["organize data efficiently"],
            "blank_count": 1,
            "answer_tolerance": "case_insensitive",
            "explanation": "Fallback FIB generated due to malformed LLM JSON.",
            "expected_time_seconds": settings.EXPECTED_TIMES.get("fib", 45),
        }

    if qtype == QType.SHORT:
        return {
            "question_text": f"Briefly explain the role of {sub_topic} in {section_topic}.",
            "model_answer": f"{sub_topic} is a core part of {section_topic} used to improve correctness and efficiency.",
            "keywords": [sub_topic, section_topic, "efficiency"],
            "min_words": 20,
            "max_words": 60,
            "explanation": "Fallback short-answer generated due to malformed LLM JSON.",
            "expected_time_seconds": settings.EXPECTED_TIMES.get("short", 120),
        }

    if qtype == QType.MSQ:
        return {
            "question_text": f"Which statements about {sub_topic} in {section_topic} are true? Select ALL that apply.",
            "options": [
                f"A. {sub_topic} can improve problem solving.",
                f"B. {sub_topic} can impact performance.",
                "C. It is never used in real systems.",
                "D. It has no trade-offs.",
                "E. It can be analyzed with complexity concepts.",
            ],
            "correct_answers": [
                f"A. {sub_topic} can improve problem solving.",
                f"B. {sub_topic} can impact performance.",
                "E. It can be analyzed with complexity concepts.",
            ],
            "explanation": "Fallback MSQ generated due to malformed LLM JSON.",
            "expected_time_seconds": settings.EXPECTED_TIMES.get("msq", 90),
        }

    if qtype == QType.NUMERICAL:
        return {
            "question_text": f"An operation in {sub_topic} takes 12 ms and runs 5 times. What is total time in ms?",
            "correct_value": 60.0,
            "unit": "ms",
            "tolerance": 0.0,
            "formula": "total = time_per_run * runs",
            "explanation": "Fallback numerical generated due to malformed LLM JSON.",
            "expected_time_seconds": settings.EXPECTED_TIMES.get("numerical", 90),
        }

    if qtype == QType.LONG:
        return {
            "question_text": f"Discuss how {sub_topic} influences design decisions in {section_topic}.",
            "rubric": {
                "points": [
                    {"point": "Concept explanation", "marks": 35, "keywords": [sub_topic]},
                    {"point": "Practical implications", "marks": 35, "keywords": ["trade-offs", "performance"]},
                    {"point": "Examples", "marks": 30, "keywords": ["example", "application"]},
                ],
                "total_marks": 100,
                "min_areas": 2,
            },
            "word_limit": {"min": 250, "max": 500},
            "requires_examples": True,
            "explanation": "Fallback long-answer generated due to malformed LLM JSON.",
            "expected_time_seconds": settings.EXPECTED_TIMES.get("long", 480),
        }

    return {
        "question_text": f"Write a function for a basic {sub_topic} task in {section_topic}.",
        "function_signature": "def solve(x):",
        "test_cases": {
            "tc_1": {"input": {"x": 1}, "output": 1, "category": "basic"},
            "tc_2": {"input": {"x": 2}, "output": 2, "category": "basic"},
        },
        "constraints": {"time_complexity": "O(n)", "space_complexity": "O(1)"},
        "explanation": "Fallback coding question generated due to malformed LLM JSON.",
        "expected_time_seconds": settings.EXPECTED_TIMES.get("coding", 900),
    }


def _parse_or_recover_llm_json(raw: str, qtype: QType, section_topic: str, sub_topic: str, difficulty: DifficultyLevel, bloom: str) -> dict:
    try:
        return parse_llm_json(raw)
    except Exception as parse_error:
        print(f"[question_generator] JSON parse failed ({parse_error}); attempting repair...")

    repair_prompt = HumanMessage(
        content=(
            "Fix the following malformed JSON and return only valid JSON. "
            f"Keep semantics aligned to section '{section_topic}', sub-topic '{sub_topic}', qtype '{qtype.value}'.\n\n"
            f"Malformed JSON:\n{raw}"
        )
    )

    try:
        repaired_raw = invoke_with_fallback([repair_prompt])
        return parse_llm_json(repaired_raw)
    except Exception as repair_error:
        print(f"[question_generator] JSON repair failed ({repair_error}); using deterministic fallback payload.")
        return _fallback_question_payload(qtype, section_topic, sub_topic, difficulty, bloom)


def _normalize_test_cases(test_cases) -> dict:
    """Accept LLM outputs in dict or list form and normalize to dict for schema.
    
    VALIDATES: Each test case must have non-empty output field.
    """
    if isinstance(test_cases, dict):
        # Validate dict format
        validated = {}
        for tc_id, case in test_cases.items():
            if isinstance(case, dict):
                output = case.get("output")
                # ✅ VALIDATION: Check for empty output
                if output is None or (isinstance(output, str) and output.strip() == ""):
                    print(f"[question_generator] ⚠️  Test case '{tc_id}' has EMPTY output field. "
                          f"This will cause validation failures in the coding backend. "
                          f"Input was: {case.get('input')}")
                
                validated[tc_id] = {
                    "input": case.get("input", {}),
                    "output": output,
                    "category": case.get("category", "basic"),
                }
            else:
                print(f"[question_generator] ⚠️  Test case '{tc_id}' is not a dict, skipping.")
                continue
        return validated

    if isinstance(test_cases, list):
        normalized = {}
        for idx, case in enumerate(test_cases, 1):
            if isinstance(case, dict):
                output = case.get("output")
                # ✅ VALIDATION: Check for empty output
                if output is None or (isinstance(output, str) and output.strip() == ""):
                    print(f"[question_generator] ⚠️  Test case 'tc_{idx}' has EMPTY output field. "
                          f"Input was: {case.get('input')}")
                
                normalized[f"tc_{idx}"] = {
                    "input": case.get("input", {}),
                    "output": output,
                    "category": case.get("category", "basic"),
                }
            else:
                normalized[f"tc_{idx}"] = {
                    "input": {},
                    "output": case,
                    "category": "basic",
                }
        return normalized
    return {}

    return {}


def _normalize_str_list(value) -> list[str]:
    """Normalize arbitrary LLM output into a clean list[str]."""
    if value is None:
        return []

    if isinstance(value, list):
        normalized = []
        for item in value:
            if item is None:
                continue
            text = str(item).strip()
            if text:
                normalized.append(text)
        return normalized

    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []

    text = str(value).strip()
    return [text] if text else []


def _normalize_int_list(value) -> list[int]:
    """Normalize arbitrary LLM output into list[int], ignoring invalid values."""
    if value is None:
        return []

    if not isinstance(value, list):
        value = [value]

    normalized = []
    for item in value:
        try:
            normalized.append(int(item))
        except (TypeError, ValueError):
            continue
    return normalized


def _normalize_choice_answers(correct_answers, options: list[str]) -> list[str]:
    """
    Normalize MCQ/MSQ correct_answers into actual option text.

    Accepts answer forms like:
    - option text (preferred)
    - 1-based/0-based indices ("1", 2)
    - letters ("A", "B", ...)
    """
    answers = _normalize_str_list(correct_answers)
    if not answers:
        return []

    if not options:
        return answers

    normalized: list[str] = []
    option_count = len(options)

    for raw in answers:
        token = raw.strip()
        if not token:
            continue

        mapped = None

        # Letter form: A/B/C/D...
        if len(token) == 1 and token.isalpha():
            idx = ord(token.upper()) - ord("A")
            if 0 <= idx < option_count:
                mapped = options[idx]

        # Numeric form: prefer 1-based, then 0-based fallback.
        if mapped is None and token.isdigit():
            n = int(token)
            if 1 <= n <= option_count:
                mapped = options[n - 1]
            elif 0 <= n < option_count:
                mapped = options[n]

        # Already option text.
        if mapped is None:
            for opt in options:
                if token.lower() == opt.strip().lower():
                    mapped = opt
                    break

        normalized.append(mapped or token)

    # De-duplicate while preserving order.
    deduped: list[str] = []
    seen = set()
    for item in normalized:
        key = item.strip().lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def question_generator(state: JITGraphState) -> dict:
    session = state["session"]
    config  = session.config

    difficulty = session.current_difficulty
    sub_topic  = session.current_sub_topic
    bloom      = DIFFICULTY_TO_BLOOM[difficulty]

    # Determine qtype for this question
    if config.question_type == QType.MIXED:
        q_num   = session.questions_asked
        qtype   = MIXED_ROTATION[q_num % len(MIXED_ROTATION)]
    else:
        qtype = config.question_type

    # Seen question snippets for dedup (last 5)
    seen = [t[:60] for t in session.seen_question_texts[-5:]]

    prompt_tmpl = PROMPT_MAP.get(qtype, MCQ_GEN_PROMPT)
    prompt = prompt_tmpl.format_messages(
        section_topic=config.section_topic,
        sub_topic=sub_topic,
        difficulty=difficulty.value,
        bloom_level=bloom.value,
        seen_questions=seen or "none",
    )

    raw  = invoke_with_fallback(prompt)
    data = _parse_or_recover_llm_json(
        raw=raw,
        qtype=qtype,
        section_topic=config.section_topic,
        sub_topic=sub_topic,
        difficulty=difficulty,
        bloom=bloom.value,
    )

    q_num = session.questions_asked + 1
    q_id  = new_question_id(session.session_id, q_num)

    # Build GeneratedQuestion from LLM data
    expected_time = int(data.get(
        "expected_time_seconds",
        settings.EXPECTED_TIMES.get(qtype.value, 60)
    ))

    normalized_test_cases = _normalize_test_cases(data.get("test_cases", {}))
    normalized_options = _normalize_str_list(data.get("options", []))
    normalized_correct_answers = _normalize_str_list(data.get("correct_answers", []))
    normalized_blank_positions = _normalize_int_list(data.get("blank_positions", []))
    normalized_keywords = _normalize_str_list(data.get("keywords", []))
    normalized_hints = _normalize_str_list(data.get("hints", []))

    if qtype in (QType.MCQ, QType.MSQ):
        normalized_correct_answers = _normalize_choice_answers(
            normalized_correct_answers,
            normalized_options,
        )

    question = GeneratedQuestion(
        question_id=q_id,
        session_id=session.session_id,
        question_number=q_num,
        qtype=qtype,
        difficulty=difficulty,
        bloom_level=bloom,
        sub_topic=sub_topic,
        question_text=str(data.get("question_text", "")).strip(),
        # MCQ / MSQ
        options=normalized_options,
        correct_answers=normalized_correct_answers,
        # FIB
        blank_positions=normalized_blank_positions,
        # Numerical
        correct_value=data.get("correct_value"),
        unit=data.get("unit", ""),
        tolerance=float(data.get("tolerance", 0.0)),
        # Short / Long
        model_answer=data.get("model_answer", ""),
        keywords=normalized_keywords,
        word_limit=data.get("word_limit"),
        rubric=data.get("rubric"),
        # Coding
        function_signature=data.get("function_signature", ""),
        test_cases=normalized_test_cases,
        # Meta
        expected_time_seconds=expected_time,
        hints=normalized_hints,
    )

    # Save pending question in session
    session.pending_question = question
    session.seen_question_texts.append(question.question_text)

    print(
        f"[question_generator] Q{q_num} | {qtype.value} | "
        f"diff={difficulty.value} | sub_topic='{sub_topic}'"
    )
    return {"session": session, "current_question": question, "action": "wait_for_answer"}