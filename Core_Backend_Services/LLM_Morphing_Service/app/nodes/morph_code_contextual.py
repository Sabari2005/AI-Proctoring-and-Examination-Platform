"""
morph_code_contextual.py
─────────────────────────
Wraps the same algorithm in a real-world scenario.
Test case VALUES stay identical; variable names adapt to match new domain.

LLM calls     : 1
TCs change    : Variable names only (values unchanged)
answer_changed: False
"""
import json
from app.core.coding_state import CodingMorphState
from app.core.coding_schemas import MorphedCodingQuestion, TestCase
from app.llm.providers import invoke_with_fallback
from app.llm.coding_prompts import CODING_CONTEXTUAL_PROMPT
from app.utils.json_parser import parse_llm_json
from app.utils.similarity import compute_similarity


def morph_code_contextual(state: CodingMorphState) -> dict:
    inp      = state["input"]
    analysis = state.get("analysis_result", {})

    tc_dict = {
        name: {"input": tc.input, "output": tc.output, "category": tc.category}
        for name, tc in inp.test_cases.items()
    }

    prompt = CODING_CONTEXTUAL_PROMPT.format_messages(
        question=inp.question,
        test_cases=json.dumps(tc_dict, default=str),
        algorithm_category=analysis.get("algorithm_category", ""),
        core_logic=analysis.get("core_logic", ""),
        function_signature=inp.function_signature,
    )

    raw = invoke_with_fallback(prompt)

    try:
        data         = parse_llm_json(raw)
        new_question = data["question"]
        new_sig      = data.get("function_signature", inp.function_signature)

        # Rebuild test cases — keep original TC objects, LLM may rename vars
        raw_tcs = data.get("test_cases", {})
        if raw_tcs and isinstance(raw_tcs, dict):
            new_tcs = {}
            orig_list = list(inp.test_cases.items())
            for i, (tc_name, tc_data) in enumerate(raw_tcs.items()):
                orig_tc = orig_list[i][1] if i < len(orig_list) else None
                new_tcs[tc_name] = TestCase(
                    input=tc_data.get("input", orig_tc.input if orig_tc else {}),
                    output=tc_data.get("output", orig_tc.output if orig_tc else None),
                    category=tc_data.get("category", "basic"),
                    explanation=tc_data.get("explanation", "Domain-shifted test case"),
                )
        else:
            new_tcs = inp.test_cases      # fallback: keep originals

    except Exception as e:
        print(f"[morph_code_contextual] Parse error: {e}. Keeping originals.")
        new_question = inp.question
        new_sig      = inp.function_signature
        new_tcs      = inp.test_cases

    semantic_score = compute_similarity(inp.question, new_question)

    quality_flags = []
    if semantic_score > 0.95:
        quality_flags.append("domain_too_similar")
    if semantic_score < 0.50:
        quality_flags.append("meaning_drift")

    variant = MorphedCodingQuestion(
        question=new_question,
        test_cases=new_tcs,
        constraints=inp.constraints,
        function_signature=new_sig,
        morph_type="code_contextual",
        difficulty_actual=inp.difficulty,
        semantic_score=round(semantic_score, 4),
        answer_changed=False,
        tc_count_original=len(inp.test_cases),
        quality_flags=quality_flags,
        explanation="Same algorithm wrapped in real-world scenario. TC values preserved.",
    )

    print(
        f"[morph_code_contextual] semantic={semantic_score:.3f} "
        f"tcs={len(new_tcs)} flags={quality_flags}"
    )
    return {"morphed_variants": [variant]}