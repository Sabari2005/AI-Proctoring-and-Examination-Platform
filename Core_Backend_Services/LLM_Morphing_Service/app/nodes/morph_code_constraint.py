"""
morph_code_constraint.py
─────────────────────────
Adds a complexity constraint that forces a different (better) algorithm.
Example: Two Sum with O(1) space → forces two-pointer instead of hash map.

The problem core stays the same. TCs mostly unchanged
(minor adjustments allowed, e.g. array must be sorted for two-pointer).

LLM calls     : 1
TCs change    : Minor (may reorder inputs to satisfy constraint like sorted array)
answer_changed: False
"""
import json
from app.core.coding_state import CodingMorphState
from app.core.coding_schemas import MorphedCodingQuestion, TestCase, CodingConstraints
from app.core.enums import DifficultyLevel
from app.llm.providers import invoke_with_fallback
from app.llm.coding_prompts import CODING_CONSTRAINT_PROMPT
from app.utils.json_parser import parse_llm_json
from app.utils.similarity import compute_similarity


# Default constraint type when not specified
DEFAULT_CONSTRAINT = "space"    # O(1) space — most universally applicable


def morph_code_constraint(state: CodingMorphState) -> dict:
    inp      = state["input"]
    analysis = state.get("analysis_result", {})

    tc_dict = {
        name: {"input": tc.input, "output": tc.output}
        for name, tc in inp.test_cases.items()
    }

    prompt = CODING_CONSTRAINT_PROMPT.format_messages(
        question=inp.question,
        test_cases=json.dumps(tc_dict, default=str),
        algorithm_category=analysis.get("algorithm_category", ""),
        function_signature=inp.function_signature,
        constraint_type=DEFAULT_CONSTRAINT,
    )

    raw = invoke_with_fallback(prompt)

    try:
        data         = parse_llm_json(raw)
        new_question = data["question"]
        new_sig      = data.get("function_signature", inp.function_signature)

        # Rebuild constraints
        raw_constraints = data.get("constraints", {})
        new_constraints = CodingConstraints(
            time_complexity=raw_constraints.get("time_complexity", inp.constraints.time_complexity),
            space_complexity=raw_constraints.get("space_complexity", "O(1)"),
            notes=raw_constraints.get("notes", []),
        )

        # Rebuild test cases — may have minor input adjustments
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
                    explanation=tc_data.get("explanation", ""),
                )
        else:
            new_tcs = inp.test_cases

    except Exception as e:
        print(f"[morph_code_constraint] Parse error: {e}. Keeping originals.")
        new_question    = inp.question + f"\n\nConstraint: Must use O(1) extra space."
        new_constraints = inp.constraints
        new_tcs         = inp.test_cases
        new_sig         = inp.function_signature

    semantic_score = compute_similarity(inp.question, new_question)

    # Constraint morphs increase difficulty by 1
    difficulty_actual = min(
        DifficultyLevel(inp.difficulty.value + 1),
        DifficultyLevel.VERY_HARD
    )

    quality_flags = []
    if semantic_score > 0.98:
        quality_flags.append("constraint_not_added")

    variant = MorphedCodingQuestion(
        question=new_question,
        test_cases=new_tcs,
        constraints=new_constraints,
        function_signature=new_sig,
        morph_type="code_constraint",
        difficulty_actual=difficulty_actual,
        semantic_score=round(semantic_score, 4),
        answer_changed=False,
        tc_count_original=len(inp.test_cases),
        quality_flags=quality_flags,
        explanation=f"Added {DEFAULT_CONSTRAINT} complexity constraint. Forces better algorithm.",
    )

    print(
        f"[morph_code_constraint] constraint={DEFAULT_CONSTRAINT} "
        f"tcs={len(new_tcs)} flags={quality_flags}"
    )
    return {"morphed_variants": [variant]}