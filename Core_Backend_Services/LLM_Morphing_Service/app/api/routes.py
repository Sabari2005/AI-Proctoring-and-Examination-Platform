from fastapi import APIRouter, HTTPException
from app.core.schemas import MorphInput, MorphOutput
from app.core.state import MorphState
from app.graph.builder import morph_graph

router = APIRouter(prefix="/api/v1", tags=["morphing"])


@router.post("/morph", response_model=MorphOutput)
async def morph_question(payload: MorphInput) -> MorphOutput:
    """
    Main endpoint. Accepts a question payload and returns morphed variants.

    Example request body:
    {
        "section": "Aptitude",
        "question": "A train travels 60 km in 1 hour. How long to travel 210 km?",
        "options": ["2.5 hours", "3.5 hours", "4 hours", "3 hours", "5 hours"],
        "correct_answer": "3.5 hours",
        "morph_config": {
            "strategies": ["rephrase", "distractor"],
            "variant_count": 2
        }
    }
    """
    initial_state: MorphState = {
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
        result = await morph_graph.ainvoke(initial_state)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Graph execution failed: {str(e)}")

    final = result.get("final_output")
    if not final:
        raise HTTPException(status_code=500, detail="Graph produced no output")

    return MorphOutput(**final)


@router.get("/health")
async def health_check():
    return {"status": "ok", "service": "llm-question-morphing"}