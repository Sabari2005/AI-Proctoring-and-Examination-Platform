"""
morph_code_tcscale.py
──────────────────────
Generates large-scale stress/performance test cases (n >= 10000).
Designed to catch O(n²) brute-force solutions that pass small inputs
but Time Limit Exceed (TLE) on large ones.

Question: UNCHANGED
Original TCs: KEPT
New TCs: n >= 10000 structured inputs with guaranteed correct outputs

LLM calls     : 1
TCs change    : Original kept + stress TCs appended
answer_changed: False
"""
import json
from app.core.coding_state import CodingMorphState
from app.core.coding_schemas import MorphedCodingQuestion, TestCase
from app.llm.providers import invoke_with_fallback
from app.llm.coding_prompts import CODING_TCSCALE_PROMPT
from app.utils.json_parser import parse_llm_json


# Naive complexity lookup — what brute force looks like
NAIVE_COMPLEXITY = {
    "O(1)":       "O(n)",
    "O(log n)":   "O(n)",
    "O(n)":       "O(n²)",
    "O(n log n)": "O(n²)",
    "O(n²)":      "O(n³)",
}


def morph_code_tcscale(state: CodingMorphState) -> dict:
    inp      = state["input"]
    analysis = state.get("analysis_result", {})

    time_complexity = analysis.get("time_complexity", "O(n)")
    naive_complexity = NAIVE_COMPLEXITY.get(time_complexity, "O(n²)")

    tc_dict = {
        name: {"input": tc.input, "output": tc.output}
        for name, tc in inp.test_cases.items()
    }

    n_stress = max(inp.morph_config.tc_count - len(inp.test_cases), 2)

    prompt = CODING_TCSCALE_PROMPT.format_messages(
        question=inp.question,
        algorithm_category=analysis.get("algorithm_category", ""),
        time_complexity=time_complexity,
        naive_complexity=naive_complexity,
        test_cases=json.dumps(tc_dict, default=str),
        function_signature=inp.function_signature,
        n_stress=n_stress,
    )

    raw = invoke_with_fallback(prompt)

    # Merge original + stress TCs
    merged_tcs = dict(inp.test_cases)

    try:
        data       = parse_llm_json(raw)
        new_sig    = data.get("function_signature", inp.function_signature)
        stress_raw = data.get("stress_test_cases", {})
        added = 0
        for tc_name, tc_data in stress_raw.items():
            if isinstance(tc_data, dict) and "input" in tc_data and "output" in tc_data:
                merged_tcs[tc_name] = TestCase(
                    input=tc_data["input"],
                    output=tc_data["output"],
                    category="stress",
                    explanation=tc_data.get("explanation", "Large-scale stress test"),
                    is_hidden=True,   # stress tests are always hidden from candidates
                )
                added += 1
        print(f"[morph_code_tcscale] Added {added} stress tests (total={len(merged_tcs)})")

    except Exception as e:
        print(f"[morph_code_tcscale] Parse error: {e}. Only original TCs kept.")
        new_sig = inp.function_signature

    quality_flags = []
    if len(merged_tcs) == len(inp.test_cases):
        quality_flags.append("no_stress_tests_added")

    variant = MorphedCodingQuestion(
        question=inp.question,
        test_cases=merged_tcs,
        constraints=inp.constraints,
        function_signature=new_sig,
        morph_type="code_tcscale",
        difficulty_actual=inp.difficulty,
        semantic_score=1.0,
        answer_changed=False,
        tc_count_original=len(inp.test_cases),
        quality_flags=quality_flags,
        explanation=(
            f"Original TCs kept. {len(merged_tcs)-len(inp.test_cases)} stress tests added. "
            f"Catches O(n²) solutions (best is {time_complexity})."
        ),
    )

    return {"morphed_variants": [variant]}