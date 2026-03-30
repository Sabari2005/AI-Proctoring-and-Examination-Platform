"""
coding_post_process.py
───────────────────────
Assembles all validated coding variants into CodingMorphOutput.
No LLM call — pure data assembly.

Reads  : morphed_variants, input, trace_id, validation_report
Writes : final_output
"""
from app.core.coding_state import CodingMorphState
from app.core.coding_schemas import CodingMorphOutput
from app.core.config import settings
from app.utils.similarity import compute_similarity


def _default_function_signature(inp) -> str:
    """Build a safe default signature from test-case input keys."""
    for tc in inp.test_cases.values():
        tc_input = getattr(tc, "input", None)
        if isinstance(tc_input, dict) and tc_input:
            args = ", ".join(f"{k}: Any" for k in tc_input.keys())
            return f"def solve({args}) -> Any:"
    return "def solve(data: Any) -> Any:"


def coding_post_process(state: CodingMorphState) -> dict:
    inp      = state["input"]
    variants = state.get("morphed_variants", [])
    trace_id = state.get("trace_id", "unknown")

    filtered_variants = []
    seen_keys = set()
    for variant in variants:
        min_score = settings.MIN_SEMANTIC_SCORE if not variant.answer_changed else 0.40
        if variant.semantic_score < min_score:
            continue

        valid_tcs = sum(
            1 for tc in variant.test_cases.values()
            if tc.input is not None and tc.output is not None
        )
        if valid_tcs < 2:
            continue

        sim_to_original = compute_similarity(inp.question, variant.question)
        is_duplicate = sim_to_original > 0.98 and variant.morph_type not in (
            "code_tcgen", "code_tcscale"
        )
        if is_duplicate:
            continue

        if "no_test_cases" in variant.quality_flags or "tc_verification_failed" in variant.quality_flags:
            continue

        dedupe_key = (variant.morph_type, variant.question.strip().lower())
        if dedupe_key in seen_keys:
            continue
        seen_keys.add(dedupe_key)
        filtered_variants.append(variant)

    if not filtered_variants and variants:
        best = max(variants, key=lambda item: item.semantic_score)
        filtered_variants = [
            best.model_copy(
                update={
                    "quality_flags": [*best.quality_flags, "below_semantic_threshold"],
                    "explanation": f"{best.explanation} (best available after retries)",
                }
            )
        ]

    default_sig = inp.function_signature.strip() or _default_function_signature(inp)
    filtered_variants = [
        v if str(getattr(v, "function_signature", "")).strip()
        else v.model_copy(update={"function_signature": default_sig})
        for v in filtered_variants
    ]

    lineage = {
        f"variant_{i}": v.morph_type
        for i, v in enumerate(filtered_variants)
    }

    failed = max(0, len(variants) - len(filtered_variants))

    output = CodingMorphOutput(
        trace_id=trace_id,
        original_question=inp.question,
        section=inp.section,
        variants=filtered_variants,
        morph_lineage=lineage,
        failed_variants=failed,
    )

    print(
        f"[coding_post_process] trace_id={trace_id} "
        f"variants={output.total_variants} failed={failed}"
    )
    return {"final_output": output.model_dump()}