"""
morph_structural node
──────────────────────
Converts the question format:
  MCQ  →  fill_blank      (removes options, inserts blank)
  MCQ  →  true_false      (yes/no or true/false format)
  MCQ  →  short_answer    (open-ended, no options)

LLM calls     : 1
Answer changes: Representation changes (e.g. "3.5 hours" stays but options drop)
Reads         : input, analysis_result
Writes        : morphed_variants (appends 1 MorphedQuestion)
"""
from app.core.state import MorphState
from app.core.schemas import MorphedQuestion
from app.core.enums import MorphStrategy, QuestionType, DifficultyLevel
from app.llm.providers import invoke_with_fallback
from app.llm.prompts import STRUCTURAL_PROMPT
from app.utils.json_parser import parse_llm_json
from app.utils.similarity import compute_similarity


# Default target format when structural morph is requested
DEFAULT_TARGET_FORMAT = "fill_blank"

FORMAT_TO_ENUM = {
    "fill_blank":    QuestionType.FILL_BLANK,
    "true_false":    QuestionType.TRUE_FALSE,
    "short_answer":  QuestionType.SHORT_ANSWER,
}


def morph_structural(state: MorphState) -> dict:
    inp = state["input"]

    # Determine target format — default to fill_blank
    to_type = DEFAULT_TARGET_FORMAT

    prompt = STRUCTURAL_PROMPT.format_messages(
        question=inp.question,
        options=", ".join(inp.options),
        correct_answer=inp.correct_answer,
        to_type=to_type,
    )

    raw = invoke_with_fallback(prompt)

    try:
        data = parse_llm_json(raw)
        new_question     = data.get("question", inp.question)
        new_correct      = data.get("correct_answer", inp.correct_answer)
        new_options      = data.get("options", [])
    except Exception as e:
        print(f"[morph_structural] Parse error: {e}. Using fallback.")
        # Manual fallback for fill_blank
        new_question = inp.question.rstrip("?") + " is ________."
        new_correct  = inp.correct_answer
        new_options  = []

    semantic_score = compute_similarity(inp.question, new_question)
    new_qtype = FORMAT_TO_ENUM.get(to_type, QuestionType.FILL_BLANK)

    quality_flags = []
    if "________" not in new_question and to_type == "fill_blank":
        quality_flags.append("blank_marker_missing")

    # Open-ended formats are slightly harder (recognition → recall)
    difficulty_actual = min(DifficultyLevel(inp.difficulty.value + 1), DifficultyLevel.VERY_HARD)

    variant = MorphedQuestion(
        question=new_question,
        options=new_options,
        correct_answer=new_correct,
        question_type=new_qtype,
        morph_type=MorphStrategy.STRUCTURAL,
        difficulty_actual=difficulty_actual,
        semantic_score=round(semantic_score, 4),
        answer_changed=False,
        quality_flags=quality_flags,
        explanation=f"Format converted from MCQ to {to_type}. Options removed, recall required.",
    )

    print(f"[morph_structural] to_type={to_type} semantic_score={semantic_score:.3f}")
    return {"morphed_variants": [variant]}