"""
post_process node
──────────────────
Final node. Assembles all validated morphed variants into the
MorphOutput schema and writes it to state["final_output"].

No LLM call — pure data assembly.

Reads  : morphed_variants, validation_report, input, trace_id
Writes : final_output (dict matching MorphOutput schema)
"""
from app.core.state import MorphState
from app.core.schemas import MorphOutput
from app.core.config import settings
from app.utils.similarity import compute_similarity


def post_process(state: MorphState) -> dict:
    inp         = state["input"]
    variants    = state.get("morphed_variants", [])
    trace_id    = state.get("trace_id", "unknown")
    report      = state.get("validation_report", {})

    target_diff = state.get("difficulty_target", inp.difficulty)

    # Keep only variants that satisfy core quality rules and de-duplicate
    filtered_variants = []
    seen_keys = set()
    for v in variants:
        if not v.answer_changed and v.semantic_score < settings.MIN_SEMANTIC_SCORE:
            continue

        difficulty_drift = abs(v.difficulty_actual.value - target_diff.value)
        if difficulty_drift > 2:
            continue

        if compute_similarity(inp.question, v.question) > 0.98:
            continue

        if "correct_answer_missing" in v.quality_flags or "answer_verification_failed" in v.quality_flags:
            continue

        dedupe_key = (v.morph_type.value, v.question.strip().lower(), v.correct_answer.strip().lower())
        if dedupe_key in seen_keys:
            continue
        seen_keys.add(dedupe_key)
        filtered_variants.append(v)

    # Build morph lineage: trace_id → strategy used for each variant
    lineage = {
        f"variant_{i}": v.morph_type.value
        for i, v in enumerate(filtered_variants)
    }

    # If no candidate fully passed, keep the best-scoring one with a clear flag.
    if not filtered_variants and variants:
        best = max(variants, key=lambda item: item.semantic_score)
        flagged = best.model_copy(
            update={
                "quality_flags": [*best.quality_flags, "below_semantic_threshold"],
                "explanation": f"{best.explanation} (best available after retries)",
            }
        )
        filtered_variants = [flagged]

    # Any removed candidate is considered failed for reporting purposes
    failed = max(0, len(variants) - len(filtered_variants))

    output = MorphOutput(
        trace_id=trace_id,
        original_question=inp.question,
        section=inp.section,
        variants=filtered_variants,
        morph_lineage=lineage,
        failed_variants=failed,
    )

    print(
        f"[post_process] trace_id={trace_id} "
        f"variants={output.total_variants} "
        f"failed={failed}"
    )

    return {"final_output": output.model_dump()}