"""
app/nodes/morph_fib.py
───────────────────────
All Fill-In-the-Blank morph nodes:
  morph_fib_rephrase    — reword sentence, keep answer
  morph_fib_contextual  — new scenario, same answer
  morph_fib_difficulty  — add more blanks
  morph_fib_multblank   — convert to multi-blank
"""
from app.core.qtype_state import QTypeMorphState
from app.core.qtype_schemas import MorphedFIB
from app.core.qtype_enums import FIBMorphStrategy
from app.llm.providers import invoke_with_fallback
from app.llm.qtype_prompts import (
    FIB_REPHRASE_PROMPT, FIB_CONTEXTUAL_PROMPT,
    FIB_DIFFICULTY_PROMPT, FIB_MULTBLANK_PROMPT,
)
from app.utils.json_parser import parse_llm_json
from app.utils.similarity import compute_similarity


def _build_fib_variant(
    state: QTypeMorphState, new_q: str, new_answers: list,
    new_positions: list, strategy: FIBMorphStrategy,
    answer_changed: bool = False, explanation: str = "",
) -> dict:
    inp            = state["input"]
    semantic_score = compute_similarity(inp.question, new_q)
    quality_flags  = []
    if "________" not in new_q and "____" not in new_q:
        quality_flags.append("blank_marker_missing")
    if semantic_score < 0.55 and not answer_changed:
        quality_flags.append("meaning_drift")

    variant = MorphedFIB(
        question=new_q,
        blank_positions=new_positions,
        correct_answers=new_answers,
        answer_tolerance=inp.answer_tolerance,
        hint=inp.hint,
        morph_type=strategy,
        difficulty_actual=state.get("difficulty_target", inp.difficulty),
        semantic_score=round(semantic_score, 4),
        answer_changed=answer_changed,
        quality_flags=quality_flags,
        explanation=explanation,
    )
    print(f"[{strategy.value}] semantic={semantic_score:.3f} flags={quality_flags}")
    return {"morphed_variants": [variant]}


def morph_fib_rephrase(state: QTypeMorphState) -> dict:
    inp      = state["input"]
    analysis = state.get("analysis_result", {})
    raw = invoke_with_fallback(FIB_REPHRASE_PROMPT.format_messages(
        question=inp.question,
        correct_answers=inp.correct_answers,
        concept=analysis.get("concept", ""),
    ))
    try:
        data = parse_llm_json(raw)
        new_q       = data.get("question", inp.question)
        new_answers = data.get("correct_answers", inp.correct_answers)
        new_pos     = data.get("blank_positions", inp.blank_positions)
    except Exception as e:
        print(f"[fib_rephrase] Parse error: {e}")
        new_q, new_answers, new_pos = inp.question, inp.correct_answers, inp.blank_positions

    return _build_fib_variant(
        state, new_q, new_answers, new_pos,
        FIBMorphStrategy.REPHRASE, False,
        "Sentence rewritten, same blank answer.",
    )


def morph_fib_contextual(state: QTypeMorphState) -> dict:
    inp      = state["input"]
    analysis = state.get("analysis_result", {})
    raw = invoke_with_fallback(FIB_CONTEXTUAL_PROMPT.format_messages(
        question=inp.question,
        correct_answers=inp.correct_answers,
        concept=analysis.get("concept", ""),
    ))
    try:
        data    = parse_llm_json(raw)
        new_q   = data.get("question", inp.question)
        new_ans = data.get("correct_answers", inp.correct_answers)
        new_pos = data.get("blank_positions", inp.blank_positions)
    except Exception as e:
        print(f"[fib_contextual] Parse error: {e}")
        new_q, new_ans, new_pos = inp.question, inp.correct_answers, inp.blank_positions

    return _build_fib_variant(
        state, new_q, new_ans, new_pos,
        FIBMorphStrategy.CONTEXTUAL, False,
        "New context testing the same fact.",
    )


def morph_fib_difficulty(state: QTypeMorphState) -> dict:
    inp           = state["input"]
    analysis      = state.get("analysis_result", {})
    target_level  = state.get("difficulty_target", inp.difficulty)
    raw = invoke_with_fallback(FIB_DIFFICULTY_PROMPT.format_messages(
        question=inp.question,
        correct_answers=inp.correct_answers,
        concept=analysis.get("concept", ""),
        target_level=target_level.value,
    ))
    try:
        data    = parse_llm_json(raw)
        new_q   = data.get("question", inp.question)
        new_ans = data.get("correct_answers", inp.correct_answers)
        new_pos = data.get("blank_positions", list(range(len(new_ans))))
    except Exception as e:
        print(f"[fib_difficulty] Parse error: {e}")
        new_q, new_ans, new_pos = inp.question, inp.correct_answers, inp.blank_positions

    answer_changed = len(new_ans) != len(inp.correct_answers)
    return _build_fib_variant(
        state, new_q, new_ans, new_pos,
        FIBMorphStrategy.DIFFICULTY, answer_changed,
        f"Difficulty adjusted to level {target_level.value}.",
    )


def morph_fib_multblank(state: QTypeMorphState) -> dict:
    inp      = state["input"]
    analysis = state.get("analysis_result", {})
    raw = invoke_with_fallback(FIB_MULTBLANK_PROMPT.format_messages(
        question=inp.question,
        correct_answers=inp.correct_answers,
        concept=analysis.get("concept", ""),
    ))
    try:
        data    = parse_llm_json(raw)
        new_q   = data.get("question", inp.question)
        new_ans = data.get("correct_answers", inp.correct_answers)
        new_pos = data.get("blank_positions", list(range(len(new_ans))))
    except Exception as e:
        print(f"[fib_multblank] Parse error: {e}")
        new_q, new_ans, new_pos = inp.question, inp.correct_answers, inp.blank_positions

    return _build_fib_variant(
        state, new_q, new_ans, new_pos,
        FIBMorphStrategy.MULTBLANK, True,
        f"Converted to {len(new_ans)}-blank question.",
    )