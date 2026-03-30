"""
morph_difficulty node
──────────────────────
Shifts the cognitive demand of the question up or down.
This is the ONLY morph that changes the correct answer.

Harder  : adds a step (extra stop, unit conversion, two-stage calc)
Easier  : removes a step, rounds numbers, or adds a hint

LLM calls     : 1
Answer changes: ALWAYS — sets answer_changed=True
Reads         : input, analysis_result, difficulty_target
Writes        : morphed_variants (appends 1 MorphedQuestion)
"""
from app.core.state import MorphState
from app.core.schemas import MorphedQuestion
from app.core.enums import MorphStrategy, DifficultyLevel
from app.llm.providers import invoke_with_fallback
from app.llm.prompts import DIFFICULTY_PROMPT
from app.utils.json_parser import parse_llm_json
from app.utils.similarity import compute_similarity


def morph_difficulty(state: MorphState) -> dict:
    inp = state["input"]
    analysis = state.get("analysis_result", {})
    difficulty_target = state.get("difficulty_target", DifficultyLevel.HARD)

    current_level = inp.difficulty.value
    target_level  = difficulty_target.value
    direction     = "harder" if target_level > current_level else "easier"

    prompt = DIFFICULTY_PROMPT.format_messages(
        question=inp.question,
        options=", ".join(inp.options),
        correct_answer=inp.correct_answer,
        concept=analysis.get("concept", ""),
        formula=analysis.get("formula", ""),
        key_values=str(analysis.get("key_values", {})),
        current_level=current_level,
        target_level=target_level,
        direction=direction,
    )

    raw = invoke_with_fallback(prompt)

    try:
        data = parse_llm_json(raw)
        new_question    = data["question"]
        new_options     = data["options"]
        new_correct     = data["correct_answer"]
        explanation     = data.get("explanation", f"Difficulty shifted {direction}.")

        # Safety: ensure correct answer is in options
        if new_correct not in new_options:
            new_options.append(new_correct)

    except Exception as e:
        print(f"[morph_difficulty] Parse error: {e}. Returning original with flag.")
        new_question = inp.question
        new_options  = inp.options
        new_correct  = inp.correct_answer
        explanation  = "Difficulty shift failed — original returned."

    semantic_score = compute_similarity(inp.question, new_question)

    quality_flags = []
    if new_correct not in new_options:
        quality_flags.append("correct_answer_missing")
    if semantic_score > 0.97:
        quality_flags.append("question_unchanged")
    if new_correct == inp.correct_answer and direction == "harder":
        quality_flags.append("answer_unchanged_expected_change")

    variant = MorphedQuestion(
        question=new_question,
        options=new_options,
        correct_answer=new_correct,
        question_type=inp.question_type,
        morph_type=MorphStrategy.DIFFICULTY,
        difficulty_actual=difficulty_target,
        semantic_score=round(semantic_score, 4),
        answer_changed=True,                    # always True for this morph
        quality_flags=quality_flags,
        explanation=explanation,
    )

    print(
        f"[morph_difficulty] direction={direction} "
        f"{current_level}→{target_level} "
        f"new_correct='{new_correct}' flags={quality_flags}"
    )
    return {"morphed_variants": [variant]}