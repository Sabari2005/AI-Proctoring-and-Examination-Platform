"""
retry_morph node
─────────────────
Triggered when validate_output fails.
Increments retry_count, injects failure context into state,
then routes back to route_morph_strategy for another attempt.

Reads  : validation_report, retry_count
Writes : retry_count
"""
from app.core.state import MorphState
from app.core.config import settings


def retry_morph(state: MorphState) -> dict:
    retry_count = state.get("retry_count", 0) + 1
    report      = state.get("validation_report", {})

    print(
        f"[retry_morph] attempt={retry_count}/{settings.MAX_RETRIES} "
        f"reasons={report.get('failure_reasons', [])}"
    )

    return {
        "retry_count":      retry_count,
        "validation_report": None,          # reset so validator runs fresh
    }