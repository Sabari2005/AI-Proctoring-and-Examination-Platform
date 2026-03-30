"""
Conditional edge functions for the LangGraph StateGraph.
Each function reads state and returns the name of the next node to visit.
"""
from app.core.state import MorphState
from app.core.enums import ValidationStatus
from app.core.config import settings


def route_after_validation(state: MorphState) -> str:
    """
    Called after validate_output.

    Returns:
        "post_process"  — if validation passed
        "retry_morph"   — if validation failed and retries remain
        "post_process"  — if max retries exceeded (fail gracefully)
    """
    report      = state.get("validation_report", {})
    retry_count = state.get("retry_count", 0)

    if report.get("status") == ValidationStatus.PASS:
        return "post_process"

    if retry_count < settings.MAX_RETRIES:
        return "retry_morph"

    # Max retries hit — go to post_process with whatever we have
    print(f"[edge] Max retries ({settings.MAX_RETRIES}) reached. Forwarding to post_process.")
    return "post_process"


def route_after_retry(state: MorphState) -> str:
    """
    After retry_morph increments the counter, always route back
    to route_morph_strategy so it re-dispatches the strategies.
    """
    return "route_morph_strategy"