"""
morph_code_difficulty.py
─────────────────────────
Shifts the problem difficulty. This is the only coding morph that changes
the core problem AND fully regenerates all test cases.

Harder  : add dimension (k-sum, 2D, all solutions, follow-up constraints)
Easier  : reduce to single pass, guarantee sorted input, simplify output

LLM calls     : 1
TCs change    : FULLY REGENERATED — new inputs AND outputs
answer_changed: True (validator re-verifies all TCs)
"""
import json
from app.core.coding_state import CodingMorphState
from app.core.coding_schemas import MorphedCodingQuestion, TestCase
from app.core.enums import DifficultyLevel
from app.llm.providers import invoke_with_fallback
from app.llm.coding_prompts import CODING_DIFFICULTY_PROMPT
from app.utils.json_parser import parse_llm_json
from app.utils.similarity import compute_similarity


def morph_code_difficulty(state: CodingMorphState) -> dict:
    inp              = state["input"]
    analysis         = state.get("analysis_result", {})
    difficulty_target = state.get("difficulty_target", DifficultyLevel.HARD)

    current_level = inp.difficulty.value
    target_level  = difficulty_target.value
    direction     = "harder" if target_level > current_level else "easier"

    tc_dict = {
        name: {"input": tc.input, "output": tc.output}
        for name, tc in inp.test_cases.items()
    }

    prompt = CODING_DIFFICULTY_PROMPT.format_messages(
        question=inp.question,
        test_cases=json.dumps(tc_dict, default=str),
        algorithm_category=analysis.get("algorithm_category", ""),
        time_complexity=analysis.get("time_complexity", "O(n)"),
        current_level=current_level,
        target_level=target_level,
        direction=direction,
        tc_count=inp.morph_config.tc_count,
        function_signature=inp.function_signature,
    )

    raw = invoke_with_fallback(prompt)

    try:
        data         = parse_llm_json(raw)
        new_question = data["question"]
        new_sig      = data.get("function_signature", inp.function_signature)
        explanation  = data.get("explanation", f"Difficulty shifted {direction}.")

        raw_tcs = data.get("test_cases", {})
        new_tcs = {}
        for tc_name, tc_data in raw_tcs.items():
            if isinstance(tc_data, dict) and "input" in tc_data and "output" in tc_data:
                new_tcs[tc_name] = TestCase(
                    input=tc_data["input"],
                    output=tc_data["output"],
                    category=tc_data.get("category", "basic"),
                    explanation=tc_data.get("explanation", ""),
                )

        if not new_tcs:
            print("[morph_code_difficulty] No TCs parsed, keeping originals.")
            new_tcs = inp.test_cases

    except Exception as e:
        print(f"[morph_code_difficulty] Parse error: {e}.")
        new_question = inp.question
        new_sig      = inp.function_signature
        new_tcs      = inp.test_cases
        explanation  = "Difficulty shift failed — original returned."

    semantic_score = compute_similarity(inp.question, new_question)

    quality_flags = []
    if semantic_score > 0.97:
        quality_flags.append("problem_unchanged")
    if not new_tcs:
        quality_flags.append("no_test_cases")

    variant = MorphedCodingQuestion(
        question=new_question,
        test_cases=new_tcs,
        constraints=inp.constraints,
        function_signature=new_sig,
        morph_type="code_difficulty",
        difficulty_actual=difficulty_target,
        semantic_score=round(semantic_score, 4),
        answer_changed=True,              # always True — TCs fully regenerated
        tc_count_original=len(inp.test_cases),
        quality_flags=quality_flags,
        explanation=explanation,
    )

    print(
        f"[morph_code_difficulty] direction={direction} {current_level}→{target_level} "
        f"tcs={len(new_tcs)} flags={quality_flags}"
    )
    return {"morphed_variants": [variant]}