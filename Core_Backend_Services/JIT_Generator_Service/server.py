"""
Standalone JIT Adaptive Assessment server.

This entrypoint is intentionally separate from app/api so it can be deployed
as an independent service (for example in a separate Lightning AI studio).

Default port: 8002
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import ValidationError

from app.core.enums import QType
from app.core.schemas import (
    AnswerSubmission,
    JITSessionConfig,
    JITSessionState,
    StartSessionResponse,
    SubmitAnswerResponse,
)
from app.core.state import JITGraphState
from app.evaluators.answer_evaluator import evaluate_answer
from app.nodes.adaptive_engine import adaptive_engine
from app.nodes.question_generator import question_generator
from app.nodes.report_generator import report_generator
from app.nodes.subtopic_extractor import extract_subtopics
from app.utils.session_store import create_session, get_session, new_session_id, update_session


app = FastAPI(
    title="JIT Adaptive Assessment Standalone Server",
    version="1.0.0",
)


def _start_session(config: JITSessionConfig) -> StartSessionResponse:
    sid = new_session_id()

    session = JITSessionState(
        session_id=sid,
        config=config,
        current_difficulty=config.start_difficulty,
        current_qtype=config.question_type if config.question_type != QType.MIXED else QType.MCQ,
        theta=float(config.start_difficulty.value),
    )

    state: JITGraphState = {
        "session": session,
        "current_question": None,
        "current_submission": None,
        "current_evaluation": None,
        "current_decision": None,
        "action": "generate",
        "error": None,
    }

    state = {**state, **extract_subtopics(state)}
    state = {**state, **question_generator(state)}

    create_session(state["session"])

    first_question = state["current_question"]
    return StartSessionResponse(
        session_id=sid,
        first_question=first_question,
        session_info={
            "num_questions": config.num_questions,
            "question_type": config.question_type.value,
            "section_topic": config.section_topic,
            "start_difficulty": config.start_difficulty.value,
            "sub_topics": state["session"].sub_topic_queue,
        },
    )


def _submit_answer(submission: AnswerSubmission) -> SubmitAnswerResponse:
    session = get_session(submission.session_id)
    if not session:
        raise ValueError(f"Session '{submission.session_id}' not found.")

    if session.status != "active":
        raise ValueError(f"Session is already '{session.status}'.")

    question = session.pending_question
    if not question:
        raise ValueError("No pending question found for this session.")

    if question.question_id != submission.question_id:
        raise ValueError(
            f"Question ID mismatch: expected {question.question_id}, got {submission.question_id}"
        )

    state: JITGraphState = {
        "session": session,
        "current_question": question,
        "current_submission": submission,
        "current_evaluation": None,
        "current_decision": None,
        "action": "evaluate",
        "error": None,
    }

    evaluation = evaluate_answer(question, submission)
    state["current_evaluation"] = evaluation

    state = {**state, **adaptive_engine(state)}
    session = state["session"]
    decision = state["current_decision"]

    if state["action"] == "report":
        state = {**state, **report_generator(state)}
        session = state["session"]
        update_session(session)
        return SubmitAnswerResponse(
            evaluation=evaluation,
            adaptive_decision=decision,
            session_complete=True,
            final_report=session.final_report,
        )

    state = {**state, **question_generator(state)}
    session = state["session"]
    update_session(session)

    return SubmitAnswerResponse(
        evaluation=evaluation,
        adaptive_decision=decision,
        next_question=state["current_question"],
        session_complete=False,
    )


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "jit-standalone",
        "endpoints": {
            "start_session": "POST /v1/session/start",
            "submit_answer": "POST /v1/session/answer",
            "status": "GET /v1/session/{session_id}/status",
            "report": "GET /v1/session/{session_id}/report",
        },
    }


@app.post("/v1/session/start", response_model=StartSessionResponse)
def start_session(config: JITSessionConfig):
    try:
        return _start_session(config)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/session/start", response_model=StartSessionResponse)
def start_session_compat(config: JITSessionConfig):
    return start_session(config)


@app.post("/v1/session/answer", response_model=SubmitAnswerResponse)
def submit_answer(submission: AnswerSubmission):
    try:
        return _submit_answer(submission)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/session/answer", response_model=SubmitAnswerResponse)
def submit_answer_compat(submission: AnswerSubmission):
    return submit_answer(submission)


@app.get("/v1/session/{session_id}/status")
def session_status(session_id: str):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session.session_id,
        "status": session.status,
        "questions_asked": session.questions_asked,
        "num_questions": session.config.num_questions,
        "theta": session.theta,
        "current_difficulty": session.current_difficulty.value,
        "streak": session.streak,
        "sub_topic_mastery": session.sub_topic_mastery,
        "difficulty_trajectory": session.difficulty_trajectory,
    }


@app.get("/session/{session_id}/status")
def session_status_compat(session_id: str):
    return session_status(session_id)


@app.get("/v1/session/{session_id}/report")
def session_report(session_id: str):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != "completed":
        raise HTTPException(status_code=400, detail="Session not yet completed")
    return session.final_report


@app.get("/session/{session_id}/report")
def session_report_compat(session_id: str):
    return session_report(session_id)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server:app", host="0.0.0.0", port=8002, reload=False)
