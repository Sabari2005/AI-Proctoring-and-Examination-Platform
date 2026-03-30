"""
JIT/app/evaluators/answer_evaluator.py
────────────────────────────────────────
Type-aware answer evaluator. Called once per submitted answer.

Scoring logic per type:
  MCQ       — exact match (1.0 or 0.0)
  FIB       — case-insensitive / exact per tolerance setting
  MSQ       — partial credit: correct_selected / total_correct - penalty_for_wrong
  Numerical — within tolerance window
  Short     — LLM rubric scoring (keywords match)
  Long      — LLM full rubric scoring
  Coding    — LLM code review + TC check
"""
import json
from typing import Any
from app.core.schemas import GeneratedQuestion, AnswerSubmission, EvaluationResult
from app.core.enums import QType, AnswerStatus
from app.core.config import settings
from app.llm.providers import invoke_with_fallback
from app.llm.prompts import SHORT_EVAL_PROMPT, LONG_EVAL_PROMPT, CODING_EVAL_PROMPT
from app.utils.json_parser import parse_llm_json


def evaluate_answer(
    question: GeneratedQuestion,
    submission: AnswerSubmission,
) -> EvaluationResult:
    """Main dispatcher — routes to type-specific evaluator."""

    qtype  = question.qtype
    answer = submission.answer

    # Handle skipped / timeout
    if answer is None or answer == "" or str(answer).strip() == "":
        status = (
            AnswerStatus.TIMEOUT if submission.time_taken_seconds >= question.expected_time_seconds * 1.5
            else AnswerStatus.SKIPPED
        )
        return _build_result(question, submission, 0.0, status, "No answer provided.")

    # Route to evaluator
    if qtype == QType.MCQ:
        score, feedback = _eval_mcq(question, answer)
    elif qtype == QType.FIB:
        score, feedback = _eval_fib(question, answer)
    elif qtype == QType.MSQ:
        score, feedback = _eval_msq(question, answer)
    elif qtype == QType.NUMERICAL:
        score, feedback = _eval_numerical(question, answer)
    elif qtype == QType.SHORT:
        score, feedback = _eval_short(question, answer)
    elif qtype == QType.LONG:
        score, feedback = _eval_long(question, answer)
    elif qtype == QType.CODING:
        score, feedback = _eval_coding(question, answer)
    else:
        score, feedback = 0.0, "Unknown question type."

    # Determine status
    if score >= 0.85:
        status = AnswerStatus.CORRECT
    elif score >= 0.40:
        status = AnswerStatus.PARTIAL
    else:
        status = AnswerStatus.WRONG

    return _build_result(question, submission, score, status, feedback)


def _build_result(
    question: GeneratedQuestion,
    submission: AnswerSubmission,
    score: float,
    status: AnswerStatus,
    feedback: str,
) -> EvaluationResult:
    # Time analysis
    time_ratio = submission.time_taken_seconds / max(question.expected_time_seconds, 1)
    if time_ratio < 0.6:
        time_bonus = 1.0
    elif time_ratio <= 1.0:
        time_bonus = 0.7
    elif time_ratio <= 1.5:
        time_bonus = 0.3
    else:
        time_bonus = 0.0

    # Confidence score (self-reported OR inferred)
    if submission.confidence:
        confidence_score = (submission.confidence - 1) / 4.0   # normalise 1-5 → 0-1
    else:
        # Infer from speed + correctness
        if score >= 0.8 and time_ratio < 0.8:
            confidence_score = 0.9
        elif score >= 0.8:
            confidence_score = 0.7
        elif score >= 0.4:
            confidence_score = 0.5
        else:
            confidence_score = 0.2

    # Reveal correct answer
    correct_reveal = _get_correct_reveal(question)

    return EvaluationResult(
        question_id=question.question_id,
        status=status,
        score=round(score, 4),
        correctness=round(score, 4),
        time_ratio=round(time_ratio, 3),
        time_bonus=round(time_bonus, 3),
        confidence_score=round(confidence_score, 3),
        feedback=feedback,
        correct_answer_reveal=correct_reveal,
    )


def _get_correct_reveal(q: GeneratedQuestion) -> Any:
    if q.qtype in (QType.MCQ, QType.MSQ, QType.FIB):
        return q.correct_answers
    elif q.qtype == QType.NUMERICAL:
        return f"{q.correct_value} {q.unit}"
    elif q.qtype == QType.SHORT:
        return q.model_answer
    elif q.qtype == QType.LONG:
        return q.rubric
    elif q.qtype == QType.CODING:
        return q.test_cases
    return None


# ── Type-specific evaluators ──────────────────────────────────────────────────

def _eval_mcq(q: GeneratedQuestion, answer: Any) -> tuple[float, str]:
    ans_str = str(answer).strip()
    correct = [c.strip() for c in q.correct_answers]
    if ans_str in correct or any(ans_str.lower() == c.lower() for c in correct):
        return 1.0, "Correct!"
    return 0.0, f"Incorrect. Correct answer: {correct[0] if correct else 'N/A'}"


def _eval_fib(q: GeneratedQuestion, answer: Any) -> tuple[float, str]:
    if isinstance(answer, list):
        student_answers = [str(a).strip() for a in answer]
    else:
        student_answers = [str(answer).strip()]

    correct = [c.strip() for c in q.correct_answers]
    matched = 0
    for sa, ca in zip(student_answers, correct):
        if sa.lower() == ca.lower():
            matched += 1

    score = matched / max(len(correct), 1)
    if score == 1.0:
        return 1.0, "All blanks correct!"
    elif score > 0:
        return score, f"{matched}/{len(correct)} blanks correct."
    return 0.0, f"Incorrect. Expected: {', '.join(correct)}"


def _eval_msq(q: GeneratedQuestion, answer: Any) -> tuple[float, str]:
    if not isinstance(answer, list):
        answer = [str(answer)]

    student = {str(a).strip().lower() for a in answer}
    correct = {c.strip().lower() for c in q.correct_answers}
    all_opts = {o.strip().lower() for o in q.options}

    true_positives  = len(student & correct)
    false_positives = len(student - correct)
    false_negatives = len(correct - student)

    # Partial credit: TP/(TP+FP+FN)
    denominator = true_positives + false_positives + false_negatives
    score = true_positives / denominator if denominator > 0 else 0.0
    feedback = f"Selected {true_positives}/{len(correct)} correct. Wrong selections: {false_positives}."
    return round(score, 3), feedback


def _eval_numerical(q: GeneratedQuestion, answer: Any) -> tuple[float, str]:
    try:
        student_val = float(str(answer).replace(",", "").strip())
    except ValueError:
        return 0.0, "Could not parse numerical answer."

    correct = q.correct_value
    tol     = q.tolerance

    if tol == 0.0:
        match = abs(student_val - correct) < 0.001
    else:
        match = abs(student_val - correct) <= tol

    if match:
        return 1.0, f"Correct! Answer: {correct} {q.unit}"
    # Partial credit for close answers (within 5% of correct)
    if correct != 0 and abs(student_val - correct) / abs(correct) <= 0.05:
        return 0.5, f"Close but not within tolerance. Expected {correct} {q.unit}, got {student_val}."
    return 0.0, f"Incorrect. Expected {correct} {q.unit}, got {student_val}."


def _eval_short(q: GeneratedQuestion, answer: str) -> tuple[float, str]:
    try:
        raw  = invoke_with_fallback(SHORT_EVAL_PROMPT.format_messages(
            question=q.question_text,
            model_answer=q.model_answer,
            keywords=q.keywords,
            student_answer=str(answer),
        ))
        data = parse_llm_json(raw)
        score    = float(data.get("score", 0.0))
        feedback = data.get("feedback", "")
        return min(score, 1.0), feedback
    except Exception as e:
        print(f"[eval_short] LLM eval error: {e}. Using keyword match.")
        return _keyword_fallback(answer, q.keywords)


def _eval_long(q: GeneratedQuestion, answer: str) -> tuple[float, str]:
    try:
        raw  = invoke_with_fallback(LONG_EVAL_PROMPT.format_messages(
            question=q.question_text,
            rubric=json.dumps(q.rubric or {}, default=str),
            student_answer=str(answer),
        ))
        data  = parse_llm_json(raw)
        score = float(data.get("total_score", 0.0))
        return min(score, 1.0), data.get("feedback", "")
    except Exception as e:
        print(f"[eval_long] LLM eval error: {e}. Scoring 0.5 as fallback.")
        return 0.5, "Answer received but could not be auto-graded. Manual review needed."


def _eval_coding(q: GeneratedQuestion, answer: str) -> tuple[float, str]:
    try:
        raw  = invoke_with_fallback(CODING_EVAL_PROMPT.format_messages(
            question=q.question_text,
            test_cases=json.dumps(q.test_cases, default=str),
            constraints=q.function_signature,
            student_answer=str(answer),
        ))
        data  = parse_llm_json(raw)
        score = float(data.get("score", 0.0))
        return min(score, 1.0), data.get("feedback", "")
    except Exception as e:
        print(f"[eval_coding] LLM eval error: {e}.")
        return 0.5, "Solution received. Manual review needed."


def _keyword_fallback(answer: str, keywords: list[str]) -> tuple[float, str]:
    if not keywords:
        return 0.5, "Answer received (no keywords to check)."
    answer_lower = answer.lower()
    matched = [kw for kw in keywords if kw.lower() in answer_lower]
    score   = len(matched) / len(keywords)
    return round(score, 2), f"Matched {len(matched)}/{len(keywords)} keywords: {matched}"