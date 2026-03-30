"""
morph_code_rephrase.py
───────────────────────
Rewrites the problem description only.
ALL test cases (inputs + outputs) stay completely unchanged.

LLM calls     : 1
TCs change    : Never
answer_changed: False
"""
from app.core.coding_state import CodingMorphState
from app.core.coding_schemas import MorphedCodingQuestion
from app.llm.providers import invoke_with_fallback
from app.llm.coding_prompts import CODING_REPHRASE_PROMPT
from app.utils.json_parser import parse_llm_json
from app.utils.similarity import compute_similarity


def morph_code_rephrase(state: CodingMorphState) -> dict:
    inp      = state["input"]
    analysis = state.get("analysis_result", {})

    prompt = CODING_REPHRASE_PROMPT.format_messages(
        question=inp.question,
        algorithm_category=analysis.get("algorithm_category", ""),
        core_logic=analysis.get("core_logic", ""),
        function_signature=inp.function_signature,
    )

    raw = invoke_with_fallback(prompt)

    try:
        data        = parse_llm_json(raw)
        new_question = data["question"]
        new_sig = data.get("function_signature", inp.function_signature)
    except Exception as e:
        print(f"[morph_code_rephrase] Parse error: {e}. Using original.")
        new_question = inp.question
        new_sig = inp.function_signature

    semantic_score = compute_similarity(inp.question, new_question)

    quality_flags = []
    if semantic_score > 0.98:
        quality_flags.append("minimal_change")
    if semantic_score < 0.65:
        quality_flags.append("meaning_drift")

    variant = MorphedCodingQuestion(
        question=new_question,
        test_cases=inp.test_cases,              # UNCHANGED
        constraints=inp.constraints,            # UNCHANGED
        function_signature=new_sig,
        morph_type="code_rephrase",
        difficulty_actual=inp.difficulty,
        semantic_score=round(semantic_score, 4),
        answer_changed=False,
        tc_count_original=len(inp.test_cases),
        quality_flags=quality_flags,
        explanation="Problem description rewritten. All test cases preserved exactly.",
    )

    print(
        f"[morph_code_rephrase] semantic={semantic_score:.3f} "
        f"tc_count={len(inp.test_cases)} flags={quality_flags}"
    )
    return {"morphed_variants": [variant]}