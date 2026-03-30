"""
app/nodes/morph_numerical.py
─────────────────────────────
All Numerical morph nodes:
  morph_numerical_rephrase   — reword, same value
  morph_numerical_contextual — new scenario, same formula+value
  morph_numerical_values     — new numbers → new correct_value
  morph_numerical_units      — unit conversion → new correct_value
  morph_numerical_difficulty — add step → new correct_value
"""
from app.core.qtype_state import QTypeMorphState
from app.core.qtype_schemas import MorphedNumerical
from app.core.qtype_enums import NumericalMorphStrategy
from app.llm.providers import invoke_with_fallback
from app.llm.qtype_prompts import (
    NUMERICAL_REPHRASE_PROMPT, NUMERICAL_CONTEXTUAL_PROMPT,
    NUMERICAL_VALUES_PROMPT, NUMERICAL_UNITS_PROMPT,
    NUMERICAL_DIFFICULTY_PROMPT,
)
from app.utils.json_parser import parse_llm_json
from app.utils.similarity import compute_similarity


def _build_numerical(
    state, new_q, new_value, new_unit, new_formula,
    strategy, answer_changed, explanation,
) -> dict:
    inp   = state["input"]
    score = compute_similarity(inp.question, new_q)
    flags = []
    if new_value is None:
        flags.append("no_correct_value")
        new_value = inp.correct_value
    if score < 0.55 and not answer_changed:
        flags.append("meaning_drift")

    variant = MorphedNumerical(
        question=new_q,
        correct_value=round(float(new_value), inp.decimal_places),
        unit=new_unit or inp.unit,
        tolerance=inp.tolerance,
        tolerance_type=inp.tolerance_type,
        decimal_places=inp.decimal_places,
        formula=new_formula or inp.formula,
        morph_type=strategy,
        difficulty_actual=state.get("difficulty_target", inp.difficulty),
        semantic_score=round(score, 4),
        answer_changed=answer_changed,
        quality_flags=flags,
        explanation=explanation,
    )
    print(f"[{strategy.value}] value={new_value} unit={new_unit} semantic={score:.3f}")
    return {"morphed_variants": [variant]}


def morph_numerical_rephrase(state: QTypeMorphState) -> dict:
    inp      = state["input"]
    analysis = state.get("analysis_result", {})
    raw = invoke_with_fallback(NUMERICAL_REPHRASE_PROMPT.format_messages(
        question=inp.question,
        correct_value=inp.correct_value,
        unit=inp.unit,
        formula=inp.formula,
        concept=analysis.get("concept", ""),
    ))
    try:
        d     = parse_llm_json(raw)
        new_q = d.get("question", inp.question)
    except Exception as e:
        print(f"[numerical_rephrase] Parse error: {e}")
        new_q = inp.question

    return _build_numerical(
        state, new_q, inp.correct_value, inp.unit, inp.formula,
        NumericalMorphStrategy.REPHRASE, False,
        "Question rephrased. Value and unit unchanged.",
    )


def morph_numerical_contextual(state: QTypeMorphState) -> dict:
    inp      = state["input"]
    analysis = state.get("analysis_result", {})
    raw = invoke_with_fallback(NUMERICAL_CONTEXTUAL_PROMPT.format_messages(
        question=inp.question,
        correct_value=inp.correct_value,
        unit=inp.unit,
        formula=inp.formula,
        concept=analysis.get("concept", ""),
    ))
    try:
        d     = parse_llm_json(raw)
        new_q = d.get("question", inp.question)
    except Exception as e:
        print(f"[numerical_contextual] Parse error: {e}")
        new_q = inp.question

    return _build_numerical(
        state, new_q, inp.correct_value, inp.unit, inp.formula,
        NumericalMorphStrategy.CONTEXTUAL, False,
        "New real-world context, same formula and answer.",
    )


def morph_numerical_values(state: QTypeMorphState) -> dict:
    inp      = state["input"]
    analysis = state.get("analysis_result", {})
    raw = invoke_with_fallback(NUMERICAL_VALUES_PROMPT.format_messages(
        question=inp.question,
        correct_value=inp.correct_value,
        unit=inp.unit,
        formula=inp.formula,
        concept=analysis.get("concept", ""),
    ))
    try:
        d         = parse_llm_json(raw)
        new_q     = d.get("question", inp.question)
        new_val   = float(d.get("correct_value", inp.correct_value))
        new_unit  = d.get("unit", inp.unit)
        expl      = d.get("explanation", "Input values changed.")
    except Exception as e:
        print(f"[numerical_values] Parse error: {e}")
        new_q, new_val, new_unit, expl = inp.question, inp.correct_value, inp.unit, ""

    return _build_numerical(
        state, new_q, new_val, new_unit, inp.formula,
        NumericalMorphStrategy.VALUES, True, expl,
    )


def morph_numerical_units(state: QTypeMorphState) -> dict:
    inp = state["input"]
    raw = invoke_with_fallback(NUMERICAL_UNITS_PROMPT.format_messages(
        question=inp.question,
        correct_value=inp.correct_value,
        unit=inp.unit,
        formula=inp.formula,
        decimal_places=inp.decimal_places,
    ))
    try:
        d        = parse_llm_json(raw)
        new_q    = d.get("question", inp.question)
        new_val  = float(d.get("correct_value", inp.correct_value))
        new_unit = d.get("unit", inp.unit)
        expl     = d.get("explanation", "Units converted.")
    except Exception as e:
        print(f"[numerical_units] Parse error: {e}")
        new_q, new_val, new_unit, expl = inp.question, inp.correct_value, inp.unit, ""

    return _build_numerical(
        state, new_q, new_val, new_unit, inp.formula,
        NumericalMorphStrategy.UNITS, True, expl,
    )


def morph_numerical_difficulty(state: QTypeMorphState) -> dict:
    inp       = state["input"]
    analysis  = state.get("analysis_result", {})
    target    = state.get("difficulty_target", inp.difficulty)
    direction = "harder" if target.value > inp.difficulty.value else "easier"
    raw = invoke_with_fallback(NUMERICAL_DIFFICULTY_PROMPT.format_messages(
        question=inp.question,
        correct_value=inp.correct_value,
        unit=inp.unit,
        formula=inp.formula,
        current_level=inp.difficulty.value,
        target_level=target.value,
        direction=direction,
    ))
    try:
        d           = parse_llm_json(raw)
        new_q       = d.get("question", inp.question)
        new_val     = float(d.get("correct_value", inp.correct_value))
        new_unit    = d.get("unit", inp.unit)
        new_formula = d.get("formula", inp.formula)
        expl        = d.get("explanation", f"Difficulty shifted {direction}.")
    except Exception as e:
        print(f"[numerical_difficulty] Parse error: {e}")
        new_q, new_val, new_unit = inp.question, inp.correct_value, inp.unit
        new_formula, expl = inp.formula, ""

    return _build_numerical(
        state, new_q, new_val, new_unit, new_formula,
        NumericalMorphStrategy.DIFFICULTY, True, expl,
    )