"""
app/nodes/morph_short.py
─────────────────────────
All Short Answer morph nodes:
  morph_short_rephrase       — reword, update model_answer
  morph_short_contextual     — new context, same concept
  morph_short_difficulty     — expand/reduce scope + word count
  morph_short_keyword_shift  — different rubric keywords, same question
"""
from app.core.qtype_state import QTypeMorphState
from app.core.qtype_schemas import MorphedShort, GradingRubric
from app.core.qtype_enums import ShortMorphStrategy
from app.llm.providers import invoke_with_fallback
from app.llm.qtype_prompts import (
    SHORT_REPHRASE_PROMPT, SHORT_CONTEXTUAL_PROMPT,
    SHORT_DIFFICULTY_PROMPT, SHORT_KEYWORD_SHIFT_PROMPT,
)
from app.utils.json_parser import parse_llm_json
from app.utils.similarity import compute_similarity


def _build_short(
    state, new_q, new_answer, new_keywords,
    new_min, new_max, strategy, answer_changed, explanation,
) -> dict:
    inp   = state["input"]
    score = compute_similarity(inp.question, new_q)
    flags = []
    if not new_keywords:
        flags.append("no_keywords")
    if score < 0.50 and not answer_changed:
        flags.append("meaning_drift")

    variant = MorphedShort(
        question=new_q,
        model_answer=new_answer,
        keywords=new_keywords,
        min_words=new_min,
        max_words=new_max,
        grading_rubric=GradingRubric(
            keywords_required=min(len(new_keywords), inp.grading_rubric.keywords_required),
            sentence_limit=inp.grading_rubric.sentence_limit,
            partial_credit=inp.grading_rubric.partial_credit,
            marks=inp.grading_rubric.marks,
        ),
        morph_type=strategy,
        difficulty_actual=state.get("difficulty_target", inp.difficulty),
        semantic_score=round(score, 4),
        answer_changed=answer_changed,
        quality_flags=flags,
        explanation=explanation,
    )
    print(f"[{strategy.value}] semantic={score:.3f} flags={flags}")
    return {"morphed_variants": [variant]}


def morph_short_rephrase(state: QTypeMorphState) -> dict:
    inp      = state["input"]
    analysis = state.get("analysis_result", {})
    raw = invoke_with_fallback(SHORT_REPHRASE_PROMPT.format_messages(
        question=inp.question,
        model_answer=inp.model_answer,
        keywords=inp.keywords,
        concept=analysis.get("concept", ""),
    ))
    try:
        d = parse_llm_json(raw)
        new_q   = d.get("question", inp.question)
        new_ans = d.get("model_answer", inp.model_answer)
        new_kw  = d.get("keywords", inp.keywords)
    except Exception as e:
        print(f"[short_rephrase] Parse error: {e}")
        new_q, new_ans, new_kw = inp.question, inp.model_answer, inp.keywords

    return _build_short(
        state, new_q, new_ans, new_kw,
        inp.min_words, inp.max_words,
        ShortMorphStrategy.REPHRASE, False,
        "Question rephrased, model answer updated.",
    )


def morph_short_contextual(state: QTypeMorphState) -> dict:
    inp      = state["input"]
    analysis = state.get("analysis_result", {})
    raw = invoke_with_fallback(SHORT_CONTEXTUAL_PROMPT.format_messages(
        question=inp.question,
        model_answer=inp.model_answer,
        keywords=inp.keywords,
        concept=analysis.get("concept", ""),
    ))
    try:
        d = parse_llm_json(raw)
        new_q   = d.get("question", inp.question)
        new_ans = d.get("model_answer", inp.model_answer)
        new_kw  = d.get("keywords", inp.keywords)
    except Exception as e:
        print(f"[short_contextual] Parse error: {e}")
        new_q, new_ans, new_kw = inp.question, inp.model_answer, inp.keywords

    return _build_short(
        state, new_q, new_ans, new_kw,
        inp.min_words, inp.max_words,
        ShortMorphStrategy.CONTEXTUAL, False,
        "New real-world context, same core concept.",
    )


def morph_short_difficulty(state: QTypeMorphState) -> dict:
    inp          = state["input"]
    analysis     = state.get("analysis_result", {})
    target       = state.get("difficulty_target", inp.difficulty)
    direction    = "harder" if target.value > inp.difficulty.value else "easier"
    raw = invoke_with_fallback(SHORT_DIFFICULTY_PROMPT.format_messages(
        question=inp.question,
        model_answer=inp.model_answer,
        keywords=inp.keywords,
        current_level=inp.difficulty.value,
        target_level=target.value,
        direction=direction,
    ))
    try:
        d       = parse_llm_json(raw)
        new_q   = d.get("question", inp.question)
        new_ans = d.get("model_answer", inp.model_answer)
        new_kw  = d.get("keywords", inp.keywords)
        new_min = int(d.get("min_words", inp.min_words))
        new_max = int(d.get("max_words", inp.max_words))
    except Exception as e:
        print(f"[short_difficulty] Parse error: {e}")
        new_q, new_ans, new_kw = inp.question, inp.model_answer, inp.keywords
        new_min, new_max = inp.min_words, inp.max_words

    return _build_short(
        state, new_q, new_ans, new_kw, new_min, new_max,
        ShortMorphStrategy.DIFFICULTY, True,
        f"Difficulty shifted {direction} to level {target.value}.",
    )


def morph_short_keyword_shift(state: QTypeMorphState) -> dict:
    inp      = state["input"]
    analysis = state.get("analysis_result", {})
    raw = invoke_with_fallback(SHORT_KEYWORD_SHIFT_PROMPT.format_messages(
        question=inp.question,
        model_answer=inp.model_answer,
        keywords=inp.keywords,
        concept=analysis.get("concept", ""),
    ))
    try:
        d       = parse_llm_json(raw)
        new_ans = d.get("model_answer", inp.model_answer)
        new_kw  = d.get("keywords", inp.keywords)
    except Exception as e:
        print(f"[short_keyword_shift] Parse error: {e}")
        new_ans, new_kw = inp.model_answer, inp.keywords

    return _build_short(
        state, inp.question, new_ans, new_kw,
        inp.min_words, inp.max_words,
        ShortMorphStrategy.KEYWORD_SHIFT, True,
        "Alternative model answer with different grading keywords.",
    )