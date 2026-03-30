"""
JIT/app/core/state.py
──────────────────────
LangGraph TypedDict flowing through the JIT adaptive graph.
One state object per question cycle — wraps the full JITSessionState.
"""
from typing import Optional
from typing_extensions import TypedDict
from .schemas import (
    JITSessionState, GeneratedQuestion,
    AnswerSubmission, EvaluationResult, AdaptiveDecision,
)


class JITGraphState(TypedDict):
    # Full session state (persisted across cycles)
    session: JITSessionState

    # Current cycle data (reset each question)
    current_question: Optional[GeneratedQuestion]
    current_submission: Optional[AnswerSubmission]
    current_evaluation: Optional[EvaluationResult]
    current_decision: Optional[AdaptiveDecision]

    # Graph control
    action: str          # "generate" | "evaluate" | "adapt" | "report"
    error: Optional[str]