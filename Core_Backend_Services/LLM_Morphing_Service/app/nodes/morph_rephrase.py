"""
morph_rephrase node
────────────────────
Rewrites the question using different vocabulary while keeping all
numbers, options, and the correct answer completely unchanged.

LLM calls     : 1
Answer changes: Never
Reads         : input, analysis_result, difficulty_target
Writes        : morphed_variants (appends 1 MorphedQuestion)
"""
from app.core.state import MorphState
from app.core.schemas import MorphedQuestion
from app.core.enums import MorphStrategy
from app.llm.providers import invoke_with_fallback
from app.llm.prompts import REPHRASE_PROMPT
from app.utils.json_parser import parse_llm_json
from app.utils.similarity import compute_similarity


def morph_rephrase(state: MorphState) -> dict:
    inp = state["input"]
    analysis = state.get("analysis_result", {})

    prompt = REPHRASE_PROMPT.format_messages(
        question=inp.question,
        options=", ".join(inp.options),
        correct_answer=inp.correct_answer,
        concept=analysis.get("concept", ""),
    )

    raw = invoke_with_fallback(prompt)

    try:
        data = parse_llm_json(raw)
        new_question = data["question"]
    except Exception as e:
        print(f"[morph_rephrase] Parse error: {e}. Returning original question.")
        new_question = inp.question

    semantic_score = compute_similarity(inp.question, new_question)

    # If LLM barely changed it, flag it
    quality_flags = []
    if semantic_score > 0.98:
        quality_flags.append("minimal_change")
    if semantic_score < 0.70:
        quality_flags.append("meaning_drift")

    variant = MorphedQuestion(
        question=new_question,
        options=inp.options,                    # options unchanged
        correct_answer=inp.correct_answer,      # answer unchanged
        question_type=inp.question_type,
        morph_type=MorphStrategy.REPHRASE,
        difficulty_actual=inp.difficulty,
        semantic_score=round(semantic_score, 4),
        answer_changed=False,
        quality_flags=quality_flags,
        explanation="Surface rewrite — same meaning, different vocabulary.",
    )

    print(f"[morph_rephrase] semantic_score={semantic_score:.3f} flags={quality_flags}")
    return {"morphed_variants": [variant]}