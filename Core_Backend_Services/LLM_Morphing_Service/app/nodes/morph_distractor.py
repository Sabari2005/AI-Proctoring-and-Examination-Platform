"""
morph_distractor node
──────────────────────
Keeps the question and correct answer unchanged.
Replaces wrong options with trap answers targeting common mistakes:
  - Integer/rounding errors
  - Inverted formula
  - Unit confusion
  - Off-by-one values

LLM calls     : 1
Answer changes: Never
Reads         : input, analysis_result
Writes        : morphed_variants (appends 1 MorphedQuestion)
"""
from app.core.state import MorphState
from app.core.schemas import MorphedQuestion
from app.core.enums import MorphStrategy, DifficultyLevel
from app.llm.providers import invoke_with_fallback
from app.llm.prompts import DISTRACTOR_PROMPT
from app.utils.json_parser import parse_llm_json
from app.utils.similarity import compute_similarity


def morph_distractor(state: MorphState) -> dict:
    inp = state["input"]
    analysis = state.get("analysis_result", {})

    # Number of distractors = total options - 1 (keep correct answer slot)
    n_distractors = len(inp.options) - 1

    prompt = DISTRACTOR_PROMPT.format_messages(
        question=inp.question,
        options=", ".join(inp.options),
        correct_answer=inp.correct_answer,
        concept=analysis.get("concept", ""),
        formula=analysis.get("formula", ""),
        n_distractors=n_distractors,
    )

    raw = invoke_with_fallback(prompt)

    try:
        data = parse_llm_json(raw)
        new_options = data["options"]

        # Safety: ensure correct answer is still in options
        if inp.correct_answer not in new_options:
            new_options.append(inp.correct_answer)

        # Deduplicate while preserving order
        seen = set()
        deduped = []
        for opt in new_options:
            if opt not in seen:
                seen.add(opt)
                deduped.append(opt)
        new_options = deduped

    except Exception as e:
        print(f"[morph_distractor] Parse error: {e}. Keeping original options.")
        new_options = inp.options

    quality_flags = []
    if inp.correct_answer not in new_options:
        quality_flags.append("correct_answer_missing")
    if len(new_options) < 3:
        quality_flags.append("too_few_options")

    # Question is unchanged — similarity is 1.0
    semantic_score = compute_similarity(inp.question, inp.question)

    # Difficulty increases because distractors are now more deceptive
    difficulty_actual = min(DifficultyLevel(inp.difficulty.value + 1), DifficultyLevel.VERY_HARD)

    variant = MorphedQuestion(
        question=inp.question,          # question unchanged
        options=new_options,
        correct_answer=inp.correct_answer,
        question_type=inp.question_type,
        morph_type=MorphStrategy.DISTRACTOR,
        difficulty_actual=difficulty_actual,
        semantic_score=round(semantic_score, 4),
        answer_changed=False,
        quality_flags=quality_flags,
        explanation="Original question kept. Wrong options replaced with trap distractors.",
    )

    print(f"[morph_distractor] new_options={new_options} flags={quality_flags}")
    return {"morphed_variants": [variant]}