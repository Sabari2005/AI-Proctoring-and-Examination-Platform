"""
app/nodes/qtype_post_process.py
────────────────────────────────
Final node — assembles all validated variants into output dict.
No LLM call.
"""
from app.core.qtype_state import QTypeMorphState
from app.core.qtype_enums import QType
from app.core.config import settings
from app.core.qtype_schemas import (
    FIBMorphOutput, ShortMorphOutput, MSQMorphOutput,
    NumericalMorphOutput, LongMorphOutput,
)
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

OUTPUT_CLASS = {
    QType.FIB:       FIBMorphOutput,
    QType.SHORT:     ShortMorphOutput,
    QType.MSQ:       MSQMorphOutput,
    QType.NUMERICAL: NumericalMorphOutput,
    QType.LONG:      LongMorphOutput,
}


def _passes_variant_checks(qtype: QType, variant) -> bool:
    score = float(getattr(variant, "semantic_score", 0.0) or 0.0)
    answer_changed = bool(getattr(variant, "answer_changed", False))
    quality_flags = set(getattr(variant, "quality_flags", []) or [])
    strategy_key = (
        variant.morph_type.value
        if hasattr(getattr(variant, "morph_type", None), "value")
        else str(getattr(variant, "morph_type", ""))
    )

    if qtype == QType.FIB:
        min_score = 0.40
    else:
        min_score = 0.35 if answer_changed else settings.MIN_SEMANTIC_SCORE
    if qtype == QType.MSQ and strategy_key == "msq_contextual":
        min_score = min(min_score, 0.50)

    if score < min_score:
        return False

    if {"blank_marker_missing", "correct_answers_empty", "model_answer_too_short", "keywords_empty", "correct_value_missing", "rubric_has_no_points", "rubric_total_marks_zero", "word_limit_min_exceeds_max"}.intersection(quality_flags):
        return False

    if qtype == QType.FIB:
        question = str(getattr(variant, "question", ""))
        correct_answers = list(getattr(variant, "correct_answers", []) or [])
        return (("________" in question) or ("____" in question)) and bool(correct_answers)

    if qtype == QType.SHORT:
        model_answer = str(getattr(variant, "model_answer", "")).strip()
        return len(model_answer) >= 5

    if qtype == QType.MSQ:
        options = list(getattr(variant, "options", []) or [])
        correct_answers = list(getattr(variant, "correct_answers", []) or [])
        return len(correct_answers) >= 2 and all(ans in options for ans in correct_answers)

    if qtype == QType.NUMERICAL:
        return getattr(variant, "correct_value", None) is not None

    if qtype == QType.LONG:
        rubric = getattr(variant, "rubric", None)
        word_limit = getattr(variant, "word_limit", None)
        if rubric is None or not getattr(rubric, "points", []):
            return False
        if getattr(rubric, "total_marks", 0) <= 0:
            return False
        if word_limit is None:
            return True
        return int(getattr(word_limit, "min", 0)) < int(getattr(word_limit, "max", 0))

    return True


def qtype_post_process(state: QTypeMorphState) -> dict:
    inp      = state["input"]
    qtype    = state["qtype"]
    variants = state.get("morphed_variants", [])
    trace_id = state.get("trace_id", "unknown")
    analysis = state.get("analysis_result") or {}
    difficulty_target = state.get("difficulty_target", inp.difficulty)
    bloom_target = state.get("bloom_target")
    difficulty_input_provided = bool(state.get("difficulty_input_provided", True))

    # Helper: safely extract bloom_level from analysis
    def extract_bloom_analyzed():
        if not analysis:
            return None
        bloom_val = analysis.get("bloom_level")
        if bloom_val is None:
            return None
        # Handle enum case
        if hasattr(bloom_val, "value"):
            return bloom_val.value
        # Handle string case
        return str(bloom_val) if bloom_val else None

    taxonomy_meta = {
        "difficulty_input": (
            int(getattr(inp.difficulty, "value", inp.difficulty))
            if difficulty_input_provided
            else None
        ),
        "difficulty_target": int(getattr(difficulty_target, "value", difficulty_target)),
        "bloom_target": (
            bloom_target.value if hasattr(bloom_target, "value") else str(bloom_target or "")
        ),
        "bloom_analyzed": extract_bloom_analyzed(),
    }

    filtered_variants = []
    seen_questions = set()

    for variant in variants:
        if not _passes_variant_checks(qtype, variant):
            continue
        qkey = str(getattr(variant, "question", "")).strip().lower()
        if qkey and qkey in seen_questions:
            continue
        if qkey:
            seen_questions.add(qkey)
        filtered_variants.append(variant)

    if not filtered_variants and variants:
        best = max(variants, key=lambda item: float(getattr(item, "semantic_score", 0.0) or 0.0))
        strategy_key = (
            best.morph_type.value
            if hasattr(getattr(best, "morph_type", None), "value")
            else str(getattr(best, "morph_type", ""))
        )

        # Avoid surfacing unsafe MSQ contextual fallbacks that drift domain/answers.
        if qtype == QType.MSQ and strategy_key == "msq_contextual":
            overlap = _domain_overlap_ratio(inp.question, str(getattr(best, "question", "")))
            question_ok = overlap >= 0.34
            options_ok = list(getattr(best, "options", []) or []) == list(inp.options)
            answers_ok = list(getattr(best, "correct_answers", []) or []) == list(inp.correct_answers)
            if not (question_ok and options_ok and answers_ok):
                print("[qtype_post_process] Skipping unsafe msq_contextual fallback variant.")
                best = None

        if best is None:
            failed = len(variants)
            cls = OUTPUT_CLASS.get(qtype)
            if cls:
                output = cls(
                    trace_id=trace_id,
                    original_question=inp.question,
                    section=inp.section,
                    variants=[],
                )
                out_dict = output.model_dump()
                out_dict["failed_variants"] = failed
                out_dict.update(taxonomy_meta)
            else:
                out_dict = {
                    "trace_id": trace_id,
                    "original_question": inp.question,
                    "section": inp.section,
                    "qtype": qtype.value,
                    "variants": [],
                    "total_variants": 0,
                    "failed_variants": failed,
                }
                out_dict.update(taxonomy_meta)
            print(
                f"[qtype_post_process] qtype={qtype.value} trace={trace_id} "
                f"variants=0 failed={failed}"
            )
            return {"final_output": out_dict}

        best_flags = list(getattr(best, "quality_flags", []) or [])
        if "validation_fallback_selected" not in best_flags:
            best_flags.append("validation_fallback_selected")
        filtered_variants = [best.model_copy(update={"quality_flags": best_flags})]

    failed = max(0, len(variants) - len(filtered_variants))

    cls = OUTPUT_CLASS.get(qtype)
    if cls:
        output = cls(
            trace_id=trace_id,
            original_question=inp.question,
            section=inp.section,
            variants=filtered_variants,
        )
        out_dict = output.model_dump()
        out_dict["failed_variants"] = failed
        out_dict.update(taxonomy_meta)
    else:
        out_dict = {
            "trace_id": trace_id,
            "original_question": inp.question,
            "section": inp.section,
            "qtype": qtype.value,
            "variants": [v.model_dump() for v in filtered_variants],
            "total_variants": len(filtered_variants),
            "failed_variants": failed,
        }
        out_dict.update(taxonomy_meta)

    print(
        f"[qtype_post_process] qtype={qtype.value} trace={trace_id} "
        f"variants={len(filtered_variants)} failed={failed}"
    )
    return {"final_output": out_dict}