"""
app/api/qtype_routes.py
────────────────────────
FastAPI routes for all 5 new question types.
Add to app/api/main.py: app.include_router(qtype_router)
"""
from fastapi import APIRouter, HTTPException
from app.core.qtype_enums import QType
from app.core.qtype_schemas import (
    FIBInput, ShortInput, MSQInput, NumericalInput, LongInput,
    FIBMorphOutput, ShortMorphOutput, MSQMorphOutput,
    NumericalMorphOutput, LongMorphOutput,
)
from app.core.qtype_state import QTypeMorphState
from app.graph.qtype_builder import qtype_graph

qtype_router = APIRouter(prefix="/api/v1", tags=["question-types"])


def _build_state(inp, qtype: QType) -> QTypeMorphState:
    return {
        "input":             inp,
        "qtype":             qtype,
        "trace_id":          "",
        "difficulty_input_provided": ("difficulty" in getattr(inp, "model_fields_set", set())),
        "analysis_result":   None,
        "difficulty_target": None,
        "bloom_target":      None,
        "morphed_variants":  [],
        "validation_report": None,
        "retry_count":       0,
        "current_strategy":  None,
        "final_output":      None,
        "error":             None,
    }


async def _run(state: QTypeMorphState):
    try:
        result = await qtype_graph.ainvoke(state)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    final = result.get("final_output")
    if not final:
        raise HTTPException(status_code=500, detail="Graph produced no output")
    return final


@qtype_router.post("/fib/morph", response_model=FIBMorphOutput)
async def morph_fib(payload: FIBInput):
    """
    Morph a fill-in-the-blank question.
    strategies: fib_rephrase | fib_contextual | fib_difficulty | fib_multblank
    """
    return FIBMorphOutput(**await _run(_build_state(payload, QType.FIB)))


@qtype_router.post("/short/morph", response_model=ShortMorphOutput)
async def morph_short(payload: ShortInput):
    """
    Morph a short-answer question.
    strategies: short_rephrase | short_contextual | short_difficulty | short_keyword_shift
    """
    return ShortMorphOutput(**await _run(_build_state(payload, QType.SHORT)))


@qtype_router.post("/msq/morph", response_model=MSQMorphOutput)
async def morph_msq(payload: MSQInput):
    """
    Morph a multiple-select question.
    strategies: msq_rephrase | msq_distractor | msq_difficulty | msq_contextual | msq_partial_rules | msq_to_mcq
    """
    return MSQMorphOutput(**await _run(_build_state(payload, QType.MSQ)))


@qtype_router.post("/numerical/morph", response_model=NumericalMorphOutput)
async def morph_numerical(payload: NumericalInput):
    """
    Morph a numerical question.
    strategies: numerical_rephrase | numerical_contextual | numerical_values | numerical_units | numerical_difficulty
    """
    return NumericalMorphOutput(**await _run(_build_state(payload, QType.NUMERICAL)))


@qtype_router.post("/long/morph", response_model=LongMorphOutput)
async def morph_long(payload: LongInput):
    """
    Morph a long-answer / essay question.
    strategies: long_rephrase | long_contextual | long_difficulty | long_focus_shift
    """
    return LongMorphOutput(**await _run(_build_state(payload, QType.LONG)))


@qtype_router.get("/strategies")
async def list_all_strategies():
    return {
        "fib":       ["fib_rephrase","fib_contextual","fib_difficulty","fib_multblank"],
        "short":     ["short_rephrase","short_contextual","short_difficulty","short_keyword_shift"],
        "msq":       ["msq_rephrase","msq_distractor","msq_difficulty","msq_contextual","msq_partial_rules","msq_to_mcq"],
        "numerical": ["numerical_rephrase","numerical_contextual","numerical_values","numerical_units","numerical_difficulty"],
        "long":      ["long_rephrase","long_contextual","long_difficulty","long_focus_shift"],
    }