"""
morph_code_tcgen.py
────────────────────
Keeps the question EXACTLY unchanged.
Generates additional NEW test cases targeting edge cases and boundary values.
All original TCs are preserved — new ones are appended.

Edge case targets:
  - Empty input
  - Single element
  - All same values / duplicates
  - Negative numbers
  - Zero values
  - Boundary values (INT_MAX, INT_MIN equivalent)
  - Cases that break naive O(n²) solutions

LLM calls     : 1
TCs change    : Original kept + new TCs appended
answer_changed: False
"""
import json
from app.core.coding_state import CodingMorphState
from app.core.coding_schemas import MorphedCodingQuestion, TestCase
from app.llm.providers import invoke_with_fallback
from app.llm.coding_prompts import CODING_TCGEN_PROMPT
from app.utils.json_parser import parse_llm_json
from app.utils.similarity import compute_similarity


def morph_code_tcgen(state: CodingMorphState) -> dict:
    inp      = state["input"]
    analysis = state.get("analysis_result", {})
    config   = inp.morph_config

    tc_dict = {
        name: {"input": tc.input, "output": tc.output, "category": tc.category}
        for name, tc in inp.test_cases.items()
    }

    # How many new TCs to add
    n_existing = len(inp.test_cases)
    n_new = max(config.tc_count - n_existing, 2)   # add at least 2 new ones

    prompt = CODING_TCGEN_PROMPT.format_messages(
        question=inp.question,
        algorithm_category=analysis.get("algorithm_category", ""),
        core_logic=analysis.get("core_logic", ""),
        test_cases=json.dumps(tc_dict, default=str),
        function_signature=inp.function_signature,
        n_new=n_new,
    )

    raw = invoke_with_fallback(prompt)

    # Merge original TCs + new TCs
    merged_tcs = dict(inp.test_cases)   # copy originals first

    try:
        data    = parse_llm_json(raw)
        new_sig = data.get("function_signature", inp.function_signature)
        new_raw = data.get("new_test_cases", {})

        added = 0
        for tc_name, tc_data in new_raw.items():
            if isinstance(tc_data, dict) and "input" in tc_data and "output" in tc_data:
                merged_tcs[tc_name] = TestCase(
                    input=tc_data["input"],
                    output=tc_data["output"],
                    category=tc_data.get("category", "edge_case"),
                    explanation=tc_data.get("explanation", ""),
                    is_hidden=False,
                )
                added += 1

        print(f"[morph_code_tcgen] Added {added} new test cases (total={len(merged_tcs)})")

    except Exception as e:
        print(f"[morph_code_tcgen] Parse error: {e}. Only original TCs kept.")
        new_sig = inp.function_signature

    semantic_score = compute_similarity(inp.question, inp.question)   # question unchanged

    quality_flags = []
    if len(merged_tcs) == len(inp.test_cases):
        quality_flags.append("no_new_tcs_added")

    variant = MorphedCodingQuestion(
        question=inp.question,          # UNCHANGED
        test_cases=merged_tcs,
        constraints=inp.constraints,
        function_signature=new_sig,
        morph_type="code_tcgen",
        difficulty_actual=inp.difficulty,
        semantic_score=1.0,             # question not changed
        answer_changed=False,
        tc_count_original=n_existing,
        quality_flags=quality_flags,
        explanation=f"Original {n_existing} TCs kept. {len(merged_tcs)-n_existing} edge-case TCs added.",
    )

    return {"morphed_variants": [variant]}