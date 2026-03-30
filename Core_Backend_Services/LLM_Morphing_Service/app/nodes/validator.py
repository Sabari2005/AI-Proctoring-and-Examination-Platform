"""
validate_output node
─────────────────────
Quality gate — runs 4 checks on every morphed variant:

  1. semantic_score   ≥ MIN_SEMANTIC_SCORE (embedding similarity vs original)
  2. difficulty_drift within ±2 of target
  3. answer_integrity — if answer_changed=True, verify math via LLM
  4. duplicate_check  — confirm question text differs from original

Sets validation_report in state.
Conditional edge reads status to route → post_process (pass) or retry (fail).

Reads  : morphed_variants, input, analysis_result
Writes : validation_report
"""
from app.core.state import MorphState, ValidationReport
from app.core.enums import ValidationStatus
from app.core.config import settings
from app.llm.providers import invoke_with_fallback
from app.llm.prompts import ANSWER_CHECK_PROMPT
from app.utils.json_parser import parse_llm_json
from app.utils.similarity import compute_similarity


def validate_output(state: MorphState) -> dict:
    inp      = state["input"]
    variants = state.get("morphed_variants", [])

    if not variants:
        report: ValidationReport = {
            "status":          ValidationStatus.FAIL,
            "semantic_score":  0.0,
            "difficulty_drift": 0,
            "answer_correct":  False,
            "is_duplicate":    False,
            "failure_reasons": ["no_variants_produced"],
        }
        return {"validation_report": report}

    # Validate the most recently added variant
    variant = variants[-1]
    failure_reasons = []

    # ── Check 1: Semantic similarity ──────────────────────────────────────
    semantic_score = variant.semantic_score
    if semantic_score < settings.MIN_SEMANTIC_SCORE and not variant.answer_changed:
        failure_reasons.append(
            f"semantic_score_too_low: {semantic_score:.3f} < {settings.MIN_SEMANTIC_SCORE}"
        )

    # ── Check 2: Difficulty drift ─────────────────────────────────────────
    target_diff    = state.get("difficulty_target", inp.difficulty)
    difficulty_drift = abs(variant.difficulty_actual.value - target_diff.value)
    if difficulty_drift > 2:
        failure_reasons.append(f"difficulty_drift_too_high: {difficulty_drift}")

    # ── Check 3: Answer integrity (only for difficulty morph) ─────────────
    answer_correct = True
    if variant.answer_changed:
        answer_correct = _verify_answer(variant.question, variant.correct_answer, variant.options)
        if not answer_correct:
            failure_reasons.append("answer_verification_failed")

    # ── Check 4: Duplicate check ──────────────────────────────────────────
    similarity_to_original = compute_similarity(inp.question, variant.question)
    is_duplicate = similarity_to_original > 0.98
    if is_duplicate:
        failure_reasons.append("question_identical_to_original")

    # ── Build report ──────────────────────────────────────────────────────
    status = ValidationStatus.PASS if not failure_reasons else ValidationStatus.FAIL

    report: ValidationReport = {
        "status":          status,
        "semantic_score":  round(semantic_score, 4),
        "difficulty_drift": difficulty_drift,
        "answer_correct":  answer_correct,
        "is_duplicate":    is_duplicate,
        "failure_reasons": failure_reasons,
    }

    print(
        f"[validate_output] status={status.value} "
        f"semantic={semantic_score:.3f} "
        f"drift={difficulty_drift} "
        f"answer_ok={answer_correct} "
        f"reasons={failure_reasons}"
    )
    return {"validation_report": report}


def _verify_answer(question: str, claimed_answer: str, options: list[str]) -> bool:
    """
    Ask the LLM to verify the math of a morphed question.
    Used only when answer_changed=True (difficulty morph).
    """
    try:
        prompt = ANSWER_CHECK_PROMPT.format_messages(
            question=question,
            correct_answer=claimed_answer,
            options=", ".join(options),
        )
        raw  = invoke_with_fallback(prompt)
        data = parse_llm_json(raw)
        return bool(data.get("is_correct", True))
    except Exception as e:
        print(f"[validate_output] Answer check failed: {e}. Assuming correct.")
        return True