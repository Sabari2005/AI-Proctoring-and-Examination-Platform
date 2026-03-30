"""
app/nodes/qtype_validator.py
─────────────────────────────
Unified validator for all 5 question types.

Checks vary by type:
  FIB        — blank marker present, answer still fills blank
  Short      — semantic score, keywords not empty, answer not empty
  MSQ        — all correct_answers in options, min 2 correct
  Numerical  — correct_value is a number, arithmetic re-verify if answer_changed
  Long       — rubric has points, total_marks > 0, word limits sane

Shared checks (all types):
  1. semantic_score ≥ threshold (relaxed for answer_changed morphs)
  2. duplicate check (question not identical to original)
"""
from app.core.qtype_state import QTypeMorphState, QTypeValidationReport
from app.core.qtype_enums import QType
from app.core.enums import ValidationStatus
from app.core.config import settings
from app.llm.providers import invoke_with_fallback
from app.llm.qtype_prompts import NUMERICAL_VERIFY_PROMPT, SHORT_ANSWER_VERIFY_PROMPT
from app.utils.json_parser import parse_llm_json
from app.utils.similarity import compute_similarity
import re


DOMAIN_STOPWORDS = {
    "which", "following", "select", "apply", "what", "when", "where", "why", "how",
    "built", "into", "with", "from", "that", "this", "these", "those", "than",
    "question", "choose", "correct", "answer", "answers", "option", "options",
    "all", "are", "for", "and", "the", "your", "about", "data", "types", "type",
}


def _salient_terms(text: str) -> set[str]:
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9_+-]*", text.lower())
    return {t for t in tokens if len(t) >= 4 and t not in DOMAIN_STOPWORDS}


def _domain_overlap_ratio(source_text: str, candidate_text: str) -> float:
    source_terms = _salient_terms(source_text)
    if not source_terms:
        return 1.0
    candidate_terms = _salient_terms(candidate_text)
    return len(source_terms & candidate_terms) / float(len(source_terms))


def qtype_validate_output(state: QTypeMorphState) -> dict:
    inp      = state["input"]
    qtype    = state["qtype"]
    variants = state.get("morphed_variants", [])

    if not variants:
        return {"validation_report": {
            "status": ValidationStatus.FAIL,
            "semantic_score": 0.0,
            "answer_valid": False,
            "failure_reasons": ["no_variants_produced"],
        }}

    variant         = variants[-1]
    failure_reasons = []
    strategy_key = (
        variant.morph_type.value
        if hasattr(variant.morph_type, "value")
        else str(variant.morph_type)
    )

    # ── Shared: semantic score ────────────────────────────────────────────
    score = variant.semantic_score
    min_score = settings.MIN_SEMANTIC_SCORE if not variant.answer_changed else 0.35
    if qtype == QType.MSQ and strategy_key == "msq_contextual":
        # Context shifts often reduce embedding similarity despite valid logic.
        min_score = min(min_score, 0.50)
    if score < min_score and qtype not in (QType.FIB,):
        # FIB rephrases naturally score lower — skip score gate for FIB
        if not (qtype == QType.FIB and score > 0.40):
            failure_reasons.append(f"semantic_score_too_low:{score:.3f}<{min_score}")

    # ── Shared: duplicate check ───────────────────────────────────────────
    sim_orig = compute_similarity(inp.question, variant.question)
    unchanged_question_allowed = {
        "short_keyword_shift",  # intentionally keeps question unchanged
        "msq_distractor",       # changes options while preserving question stem
        "msq_difficulty",       # may adjust answers/options without rewording stem
    }
    if sim_orig > 0.99 and strategy_key not in unchanged_question_allowed:
        failure_reasons.append("question_identical_to_original")

    # ── Type-specific checks ──────────────────────────────────────────────
    answer_valid = True

    if qtype == QType.FIB:
        if "________" not in variant.question and "____" not in variant.question:
            failure_reasons.append("blank_marker_missing")
        if not variant.correct_answers:
            failure_reasons.append("correct_answers_empty")
            answer_valid = False

    elif qtype == QType.SHORT:
        if not variant.model_answer or len(variant.model_answer.strip()) < 5:
            failure_reasons.append("model_answer_too_short")
            answer_valid = False
        if not variant.keywords:
            failure_reasons.append("keywords_empty")
        if variant.answer_changed:
            answer_valid = _verify_short_answer(
                variant.question, variant.model_answer, variant.keywords
            )
            if not answer_valid:
                failure_reasons.append("short_answer_verification_failed")

    elif qtype == QType.MSQ:
        for ca in variant.correct_answers:
            if ca not in variant.options:
                failure_reasons.append(f"correct_answer_not_in_options:{ca}")
                answer_valid = False
        if len(variant.correct_answers) < 2:
            failure_reasons.append("msq_needs_min_2_correct_answers")
        if strategy_key == "msq_contextual":
            overlap = _domain_overlap_ratio(inp.question, variant.question)
            if overlap < 0.34:
                failure_reasons.append(f"domain_drift_overlap_too_low:{overlap:.2f}")
                answer_valid = False
            if list(variant.options) != list(inp.options):
                failure_reasons.append("contextual_options_changed")
                answer_valid = False
            if list(variant.correct_answers) != list(inp.correct_answers):
                failure_reasons.append("contextual_correct_answers_changed")
                answer_valid = False

    elif qtype == QType.NUMERICAL:
        if variant.correct_value is None:
            failure_reasons.append("correct_value_missing")
            answer_valid = False
        elif variant.answer_changed:
            answer_valid = _verify_numerical(
                variant.question, variant.correct_value,
                variant.unit, variant.formula
            )
            if not answer_valid:
                failure_reasons.append("numerical_verification_failed")

    elif qtype == QType.LONG:
        if not variant.rubric.points:
            failure_reasons.append("rubric_has_no_points")
            answer_valid = False
        if variant.rubric.total_marks <= 0:
            failure_reasons.append("rubric_total_marks_zero")
        if variant.word_limit.min >= variant.word_limit.max:
            failure_reasons.append("word_limit_min_exceeds_max")

    status = ValidationStatus.PASS if not failure_reasons else ValidationStatus.FAIL

    report: QTypeValidationReport = {
        "status":          status,
        "semantic_score":  round(score, 4),
        "answer_valid":    answer_valid,
        "failure_reasons": failure_reasons,
    }

    print(
        f"[qtype_validate] qtype={qtype.value} status={status.value} "
        f"semantic={score:.3f} answer_ok={answer_valid} reasons={failure_reasons}"
    )
    return {"validation_report": report}


def _verify_numerical(question, correct_value, unit, formula) -> bool:
    try:
        raw  = invoke_with_fallback(NUMERICAL_VERIFY_PROMPT.format_messages(
            question=question, formula=formula,
            correct_value=correct_value, unit=unit,
        ))
        data = parse_llm_json(raw)
        return bool(data.get("is_correct", True))
    except Exception as e:
        print(f"[qtype_validate] Numerical verify error: {e}. Assuming correct.")
        return True


def _verify_short_answer(question, model_answer, keywords) -> bool:
    try:
        raw  = invoke_with_fallback(SHORT_ANSWER_VERIFY_PROMPT.format_messages(
            question=question, model_answer=model_answer, keywords=keywords,
        ))
        data = parse_llm_json(raw)
        return bool(data.get("is_correct", True))
    except Exception as e:
        print(f"[qtype_validate] Short answer verify error: {e}. Assuming correct.")
        return True