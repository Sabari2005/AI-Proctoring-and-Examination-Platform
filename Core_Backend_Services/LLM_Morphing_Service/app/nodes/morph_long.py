"""
app/nodes/morph_long.py
────────────────────────
All Long Answer morph nodes:
  morph_long_rephrase    — reword question, rubric unchanged
  morph_long_contextual  — shift time/geography, adapt rubric labels
  morph_long_difficulty  — add/remove rubric points
  morph_long_focus_shift — same topic, different rubric aspects
"""
import json
from app.core.qtype_state import QTypeMorphState
from app.core.qtype_schemas import MorphedLong, Rubric, RubricPoint, WordLimit
from app.core.qtype_enums import LongMorphStrategy
from app.llm.providers import invoke_with_fallback
from app.llm.qtype_prompts import (
    LONG_REPHRASE_PROMPT, LONG_CONTEXTUAL_PROMPT,
    LONG_DIFFICULTY_PROMPT, LONG_FOCUS_SHIFT_PROMPT,
)
from app.utils.json_parser import parse_llm_json
from app.utils.similarity import compute_similarity


def _parse_rubric(raw_rubric: dict, fallback: Rubric) -> Rubric:
    """Parse LLM rubric dict into Rubric model, with fallback."""
    try:
        points = [
            RubricPoint(
                point=p.get("point", ""),
                marks=int(p.get("marks", 0)),
                keywords=p.get("keywords", []),
            )
            for p in raw_rubric.get("points", [])
            if p.get("point")
        ]
        if not points:
            return fallback
        return Rubric(
            points=points,
            total_marks=sum(p.marks for p in points),
            min_areas=raw_rubric.get("min_areas", fallback.min_areas),
        )
    except Exception:
        return fallback


def _build_long(
    state, new_q, new_rubric, new_word_limit,
    strategy, answer_changed, explanation,
) -> dict:
    inp   = state["input"]
    score = compute_similarity(inp.question, new_q)
    flags = []
    if len(new_rubric.points) == 0:
        flags.append("empty_rubric")
    if score < 0.45 and not answer_changed:
        flags.append("meaning_drift")

    variant = MorphedLong(
        question=new_q,
        rubric=new_rubric,
        word_limit=new_word_limit,
        requires_examples=inp.requires_examples,
        morph_type=strategy,
        difficulty_actual=state.get("difficulty_target", inp.difficulty),
        semantic_score=round(score, 4),
        answer_changed=answer_changed,
        quality_flags=flags,
        explanation=explanation,
    )
    print(f"[{strategy.value}] semantic={score:.3f} rubric_points={len(new_rubric.points)}")
    return {"morphed_variants": [variant]}


def morph_long_rephrase(state: QTypeMorphState) -> dict:
    inp      = state["input"]
    analysis = state.get("analysis_result", {})
    raw = invoke_with_fallback(LONG_REPHRASE_PROMPT.format_messages(
        question=inp.question,
        rubric=json.dumps(inp.rubric.model_dump(), default=str),
        concept=analysis.get("concept", ""),
    ))
    try:
        d     = parse_llm_json(raw)
        new_q = d.get("question", inp.question)
    except Exception as e:
        print(f"[long_rephrase] Parse error: {e}")
        new_q = inp.question

    return _build_long(
        state, new_q, inp.rubric, inp.word_limit,
        LongMorphStrategy.REPHRASE, False,
        "Question rephrased. Rubric and word limits unchanged.",
    )


def morph_long_contextual(state: QTypeMorphState) -> dict:
    inp      = state["input"]
    analysis = state.get("analysis_result", {})
    raw = invoke_with_fallback(LONG_CONTEXTUAL_PROMPT.format_messages(
        question=inp.question,
        rubric=json.dumps(inp.rubric.model_dump(), default=str),
        concept=analysis.get("concept", ""),
    ))
    try:
        d         = parse_llm_json(raw)
        new_q     = d.get("question", inp.question)
        new_rubric = _parse_rubric(d.get("rubric", {}), inp.rubric)
    except Exception as e:
        print(f"[long_contextual] Parse error: {e}")
        new_q, new_rubric = inp.question, inp.rubric

    return _build_long(
        state, new_q, new_rubric, inp.word_limit,
        LongMorphStrategy.CONTEXTUAL, False,
        "Context shifted. Rubric analytical framework preserved.",
    )


def morph_long_difficulty(state: QTypeMorphState) -> dict:
    inp       = state["input"]
    analysis  = state.get("analysis_result", {})
    target    = state.get("difficulty_target", inp.difficulty)
    direction = "harder" if target.value > inp.difficulty.value else "easier"
    raw = invoke_with_fallback(LONG_DIFFICULTY_PROMPT.format_messages(
        question=inp.question,
        rubric=json.dumps(inp.rubric.model_dump(), default=str),
        word_limit=json.dumps(inp.word_limit.model_dump()),
        current_level=inp.difficulty.value,
        target_level=target.value,
        direction=direction,
    ))
    try:
        d         = parse_llm_json(raw)
        new_q     = d.get("question", inp.question)
        new_rubric = _parse_rubric(d.get("rubric", {}), inp.rubric)
        wl        = d.get("word_limit", {})
        new_wl    = WordLimit(
            min=int(wl.get("min", inp.word_limit.min)),
            max=int(wl.get("max", inp.word_limit.max)),
        )
        expl = d.get("explanation", f"Difficulty shifted {direction}.")
    except Exception as e:
        print(f"[long_difficulty] Parse error: {e}")
        new_q, new_rubric, new_wl, expl = inp.question, inp.rubric, inp.word_limit, ""

    return _build_long(
        state, new_q, new_rubric, new_wl,
        LongMorphStrategy.DIFFICULTY, True, expl,
    )


def morph_long_focus_shift(state: QTypeMorphState) -> dict:
    inp      = state["input"]
    analysis = state.get("analysis_result", {})
    raw = invoke_with_fallback(LONG_FOCUS_SHIFT_PROMPT.format_messages(
        question=inp.question,
        rubric=json.dumps(inp.rubric.model_dump(), default=str),
        concept=analysis.get("concept", ""),
    ))
    try:
        d          = parse_llm_json(raw)
        new_q      = d.get("question", inp.question)
        new_rubric = _parse_rubric(d.get("rubric", {}), inp.rubric)
    except Exception as e:
        print(f"[long_focus_shift] Parse error: {e}")
        new_q, new_rubric = inp.question, inp.rubric

    return _build_long(
        state, new_q, new_rubric, inp.word_limit,
        LongMorphStrategy.FOCUS_SHIFT, True,
        "Same topic, different analytical aspects required.",
    )