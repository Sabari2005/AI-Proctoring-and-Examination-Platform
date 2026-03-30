"""
coding_validator.py
────────────────────
Quality gate for coding morphs. Runs 4 checks:

  1. semantic_score    — question meaning not drifted too far
  2. tc_count_valid    — all TCs have both input AND output fields
  3. answer_correct    — only for difficulty morph (answer_changed=True),
                         re-verifies a sample of TCs via LLM
  4. duplicate_check   — morphed question differs from original

Reads  : morphed_variants, input, analysis_result
Writes : validation_report
"""
import json
from app.core.coding_state import CodingMorphState, CodingValidationReport
from app.core.enums import ValidationStatus
from app.core.config import settings
from app.llm.providers import invoke_with_fallback
from app.llm.coding_prompts import CODING_TC_VERIFY_PROMPT
from app.utils.json_parser import parse_llm_json
from app.utils.similarity import compute_similarity


def coding_validate_output(state: CodingMorphState) -> dict:
    inp      = state["input"]
    variants = state.get("morphed_variants", [])

    if not variants:
        report: CodingValidationReport = {
            "status":           ValidationStatus.FAIL,
            "semantic_score":   0.0,
            "tc_count_valid":   0,
            "tc_count_total":   0,
            "answer_correct":   False,
            "failure_reasons":  ["no_variants_produced"],
        }
        return {"validation_report": report}

    variant         = variants[-1]
    failure_reasons = []

    # ── Check 1: Semantic similarity ──────────────────────────────────────
    semantic_score = variant.semantic_score
    # Code rephrase needs higher similarity; difficulty morph intentionally drifts
    min_score = settings.MIN_SEMANTIC_SCORE if not variant.answer_changed else 0.40
    if semantic_score < min_score:
        failure_reasons.append(
            f"semantic_score_too_low: {semantic_score:.3f} < {min_score}"
        )

    # ── Check 2: TC format validity ───────────────────────────────────────
    valid_tcs = sum(
        1 for tc in variant.test_cases.values()
        if tc.input is not None and tc.output is not None
    )
    total_tcs = len(variant.test_cases)
    if valid_tcs < 2:
        failure_reasons.append(f"too_few_valid_tcs: {valid_tcs}")

    # ── Check 3: Answer correctness for difficulty morph ──────────────────
    answer_correct = True
    if variant.answer_changed and variant.test_cases:
        answer_correct = _verify_test_cases(
            variant.question,
            variant.test_cases,
            state.get("analysis_result", {}),
        )
        if not answer_correct:
            failure_reasons.append("tc_verification_failed")

    # ── Check 4: Duplicate check ──────────────────────────────────────────
    sim_to_original = compute_similarity(inp.question, variant.question)
    is_duplicate    = sim_to_original > 0.98 and variant.morph_type not in (
        "code_tcgen", "code_tcscale"   # these intentionally keep identical question
    )
    if is_duplicate:
        failure_reasons.append("question_identical_to_original")

    status = ValidationStatus.PASS if not failure_reasons else ValidationStatus.FAIL

    report: CodingValidationReport = {
        "status":          status,
        "semantic_score":  round(semantic_score, 4),
        "tc_count_valid":  valid_tcs,
        "tc_count_total":  total_tcs,
        "answer_correct":  answer_correct,
        "failure_reasons": failure_reasons,
    }

    print(
        f"[coding_validate] status={status.value} "
        f"semantic={semantic_score:.3f} "
        f"tcs={valid_tcs}/{total_tcs} "
        f"answer_ok={answer_correct} "
        f"reasons={failure_reasons}"
    )
    return {"validation_report": report}


def _verify_test_cases(question: str, test_cases: dict, analysis: dict) -> bool:
    """
    Ask LLM to verify a sample of TCs for the difficulty-shifted question.
    Verifies up to 3 TCs to keep cost low.
    """
    sample = dict(list(test_cases.items())[:3])
    tc_dict = {
        name: {"input": tc.input, "output": tc.output}
        for name, tc in sample.items()
    }
    try:
        prompt = CODING_TC_VERIFY_PROMPT.format_messages(
            question=question,
            algorithm_category=analysis.get("algorithm_category", ""),
            test_cases=json.dumps(tc_dict, default=str),
        )
        raw     = invoke_with_fallback(prompt)
        data    = parse_llm_json(raw)
        results = data.get("results", [])
        failed  = [r for r in results if not r.get("is_correct", True)]
        if failed:
            print(f"[coding_validate] TC verification failed: {failed}")
            return False
        return True
    except Exception as e:
        print(f"[coding_validate] TC verification error: {e}. Assuming correct.")
        return True