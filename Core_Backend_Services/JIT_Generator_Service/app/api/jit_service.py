"""
JIT/app/api/jit_service.py
───────────────────────────
Service layer — coordinates session store, evaluator, and adaptive engine.
FastAPI routes call these functions.
"""
from app.core.schemas import (
    JITSessionConfig, JITSessionState, GeneratedQuestion,
    AnswerSubmission, EvaluationResult, AdaptiveDecision,
    StartSessionResponse, SubmitAnswerResponse,
)
from app.core.enums import QType, DifficultyLevel
from app.core.state import JITGraphState
from app.evaluators.answer_evaluator import evaluate_answer
from app.nodes.subtopic_extractor import extract_subtopics
from app.nodes.question_generator import question_generator
from app.nodes.adaptive_engine import adaptive_engine
from app.nodes.report_generator import report_generator
from app.utils.jit_db_store import persist_final_report, persist_session_start
from app.utils.session_store import (
    create_session, get_session, update_session, new_session_id,
)


def start_session(config: JITSessionConfig) -> StartSessionResponse:
    """
    Initialise a new JIT session and generate the first question.
    Returns session_id + first question JSON.
    """
    sid = new_session_id()

    session = JITSessionState(
        session_id=sid,
        config=config,
        current_difficulty=config.start_difficulty,
        current_qtype=config.question_type if config.question_type != QType.MIXED else QType.MCQ,
        theta=float(config.start_difficulty.value),
    )

    # Build initial graph state
    graph_state: JITGraphState = {
        "session":             session,
        "current_question":    None,
        "current_submission":  None,
        "current_evaluation":  None,
        "current_decision":    None,
        "action":              "generate",
        "error":               None,
    }

    # Step 1: extract sub-topics
    graph_state = {**graph_state, **extract_subtopics(graph_state)}

    # Step 2: generate first question
    graph_state = {**graph_state, **question_generator(graph_state)}

    # Persist session
    create_session(graph_state["session"])
    # Best-effort DB bind so jit_section_sessions tracks active JIT session_id at start.
    persist_session_start(
        session_id=sid,
        candidate_id=config.candidate_id,
        section_topic=config.section_topic,
    )

    question = graph_state["current_question"]
    return StartSessionResponse(
        session_id=sid,
        first_question=question,
        session_info={
            "num_questions":    config.num_questions,
            "question_type":    config.question_type.value,
            "section_topic":    config.section_topic,
            "start_difficulty": config.start_difficulty.value,
            "sub_topics":       graph_state["session"].sub_topic_queue,
        },
    )


def submit_answer(submission: AnswerSubmission) -> SubmitAnswerResponse:
    """
    Accept a candidate's answer, evaluate it, run adaptive engine,
    and return next question or final report.
    """
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
            f"Question ID mismatch: expected {question.question_id}, "
            f"got {submission.question_id}"
        )

    # Build graph state for this cycle
    graph_state: JITGraphState = {
        "session":             session,
        "current_question":    question,
        "current_submission":  submission,
        "current_evaluation":  None,
        "current_decision":    None,
        "action":              "evaluate",
        "error":               None,
    }

    # Step 1: evaluate answer
    evaluation = evaluate_answer(question, submission)
    graph_state["current_evaluation"] = evaluation

    # Step 2: adaptive engine
    graph_state = {**graph_state, **adaptive_engine(graph_state)}
    session     = graph_state["session"]
    decision    = graph_state["current_decision"]

    # Step 3: generate next question OR report
    session_complete = graph_state["action"] == "report"

    if session_complete:
        graph_state = {**graph_state, **report_generator(graph_state)}
        session     = graph_state["session"]
        # Persist final report directly from JIT service so DB write does not
        # depend on mock_server-side forwarding logic.
        persist_final_report(session.session_id, session.final_report)
        update_session(session)
        return SubmitAnswerResponse(
            evaluation=evaluation,
            adaptive_decision=decision,
            session_complete=True,
            final_report=session.final_report,
        )

    # Generate next question
    graph_state = {**graph_state, **question_generator(graph_state)}
    session     = graph_state["session"]
    update_session(session)

    return SubmitAnswerResponse(
        evaluation=evaluation,
        adaptive_decision=decision,
        next_question=graph_state["current_question"],
        session_complete=False,
    )


def get_session_status(session_id: str) -> dict:
    """Return current session progress summary."""
    session = get_session(session_id)
    if not session:
        raise ValueError(f"Session '{session_id}' not found.")

    return {
        "session_id":         session.session_id,
        "status":             session.status,
        "questions_asked":    session.questions_asked,
        "num_questions":      session.config.num_questions,
        "theta":              session.theta,
        "current_difficulty": session.current_difficulty.value,
        "streak":             session.streak,
        "sub_topic_mastery":  session.sub_topic_mastery,
        "difficulty_trajectory": session.difficulty_trajectory,
    }


def get_final_report(session_id: str) -> dict:
    """Return final report for a completed session."""
    session = get_session(session_id)
    if not session:
        raise ValueError(f"Session '{session_id}' not found.")
    if session.status != "completed":
        raise ValueError("Session not yet completed.")
    return session.final_report