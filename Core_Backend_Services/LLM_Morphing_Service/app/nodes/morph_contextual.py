"""
morph_contextual node
──────────────────────
Wraps the same math/logic in a new real-world scenario.
Same numbers, same formula, same answer — only the story changes.

LLM calls     : 1
Answer changes: Never
Reads         : input, analysis_result
Writes        : morphed_variants (appends 1 MorphedQuestion)
"""
from app.core.state import MorphState
from app.core.schemas import MorphedQuestion
from app.core.enums import MorphStrategy
from app.llm.providers import invoke_with_fallback
from app.llm.prompts import CONTEXTUAL_PROMPT
from app.utils.json_parser import parse_llm_json
from app.utils.similarity import compute_similarity


def morph_contextual(state: MorphState) -> dict:
    inp = state["input"]
    analysis = state.get("analysis_result", {})

    prompt = CONTEXTUAL_PROMPT.format_messages(
        question=inp.question,
        options=", ".join(inp.options),
        correct_answer=inp.correct_answer,
        formula=analysis.get("formula", ""),
        key_values=str(analysis.get("key_values", {})),
    )

    raw = invoke_with_fallback(prompt)

    try:
        data = parse_llm_json(raw)
        new_question = data["question"]
    except Exception as e:
        print(f"[morph_contextual] Parse error: {e}.")
        new_question = inp.question

    semantic_score = compute_similarity(inp.question, new_question)

    quality_flags = []
    if semantic_score > 0.95:
        quality_flags.append("domain_too_similar")
    if semantic_score < 0.55:
        quality_flags.append("meaning_drift")

    variant = MorphedQuestion(
        question=new_question,
        options=inp.options,
        correct_answer=inp.correct_answer,
        question_type=inp.question_type,
        morph_type=MorphStrategy.CONTEXTUAL,
        difficulty_actual=inp.difficulty,
        semantic_score=round(semantic_score, 4),
        answer_changed=False,
        quality_flags=quality_flags,
        explanation="New real-world scenario embedding the same formula and values.",
    )

    print(f"[morph_contextual] semantic_score={semantic_score:.3f} flags={quality_flags}")
    return {"morphed_variants": [variant]}