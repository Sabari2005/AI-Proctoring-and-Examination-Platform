"""
JIT/app/api/routes.py
──────────────────────
FastAPI endpoints for the JIT adaptive assessment engine.

Flow:
  POST /session/start          → returns session_id + first question
  POST /session/answer         → submit answer → get evaluation + next question
  GET  /session/{id}/status    → current progress
  GET  /session/{id}/report    → final report (when complete)
"""
from fastapi import APIRouter, HTTPException
from app.core.schemas import (
    JITSessionConfig, AnswerSubmission,
    StartSessionResponse, SubmitAnswerResponse,
)
from app.api.jit_service import (
    start_session, submit_answer,
    get_session_status, get_final_report,
)

router = APIRouter(prefix="/api/v1/jit", tags=["JIT Adaptive Assessment"])


@router.post("/session/start", response_model=StartSessionResponse)
async def api_start_session(config: JITSessionConfig):
    """
    Start a new adaptive assessment session.

    Example request:
    {
        "section_topic": "Operating Systems",
        "num_questions": 10,
        "question_type": "mcq",
        "start_difficulty": 2,
        "candidate_id": "student_001"
    }
    """
    try:
        return start_session(config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/session/answer", response_model=SubmitAnswerResponse)
async def api_submit_answer(submission: AnswerSubmission):
    """
    Submit an answer for the current pending question.

    Example request:
    {
        "session_id": "jit-abc123",
        "question_id": "jit-abc123-q01",
        "question_number": 1,
        "answer": "A. The kernel",
        "time_taken_seconds": 45,
        "confidence": 4
    }

    For MSQ: answer = ["A. ...", "C. ..."]
    For Numerical: answer = 200.0
    For FIB multi-blank: answer = ["Paris", "France"]
    For Short/Long/Coding: answer = "string of text / code"
    """
    try:
        return submit_answer(submission)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}/status")
async def api_session_status(session_id: str):
    """Get current session progress."""
    try:
        return get_session_status(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/session/{session_id}/report")
async def api_final_report(session_id: str):
    """Get final assessment report (only available after session completes)."""
    try:
        return get_final_report(session_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/question-types")
async def api_question_types():
    """List supported question types."""
    return {
        "types": ["mcq", "fib", "short", "msq", "numerical", "long", "coding", "mixed"],
        "mixed": "Rotates automatically through all types",
    }