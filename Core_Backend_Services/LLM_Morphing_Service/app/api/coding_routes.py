"""
app/api/coding_routes.py
─────────────────────────
FastAPI route for the coding question morphing pipeline.
Add this to app/api/main.py: app.include_router(coding_router)
"""
from fastapi import APIRouter, HTTPException
from app.core.coding_schemas import CodingMorphInput, CodingMorphOutput
from app.core.coding_state import CodingMorphState
from app.graph.coding_builder import coding_morph_graph

coding_router = APIRouter(prefix="/api/v1/coding", tags=["coding-morphing"])


@coding_router.post("/morph", response_model=CodingMorphOutput)
async def morph_coding_question(payload: CodingMorphInput) -> CodingMorphOutput:
    """
    Morph a coding question with test cases.

    Example request body:
    {
        "section": "Coding",
        "question": "Given an array nums and a target, return indices of two numbers that add up to target.",
        "test_cases": {
            "tc_1": {"input": {"nums": [2,7,11,15], "target": 9}, "output": [0,1]},
            "tc_2": {"input": {"nums": [3,2,4], "target": 6}, "output": [1,2]},
            "tc_3": {"input": {"nums": [3,3], "target": 6}, "output": [0,1]}
        },
        "function_signature": "def twoSum(nums: list[int], target: int) -> list[int]:",
        "topic_tags": ["array", "hash-map"],
        "morph_config": {
            "strategies": ["code_rephrase", "code_tcgen"],
            "tc_count": 6
        }
    }
    """
    initial_state: CodingMorphState = {
        "input":             payload,
        "trace_id":          "",
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

    try:
        result = await coding_morph_graph.ainvoke(initial_state)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Coding graph failed: {str(e)}")

    final = result.get("final_output")
    if not final:
        raise HTTPException(status_code=500, detail="Coding graph produced no output")

    return CodingMorphOutput(**final)


@coding_router.get("/strategies")
async def list_strategies():
    return {
        "strategies": [
            {"id": "code_rephrase",   "description": "Rephrase question text, TCs unchanged"},
            {"id": "code_contextual", "description": "Real-world scenario wrap, same algorithm"},
            {"id": "code_difficulty", "description": "Shift difficulty, regenerate all TCs"},
            {"id": "code_constraint", "description": "Add time/space constraint"},
            {"id": "code_tcgen",      "description": "Generate additional edge-case TCs"},
            {"id": "code_tcscale",    "description": "Generate large-scale stress TCs"},
        ]
    }