"""
app/graph/qtype_builder.py
───────────────────────────
Assembles one unified StateGraph for all 5 question types.
The same graph handles FIB, Short, MSQ, Numerical, and Long —
the router dispatches to the right morph nodes based on strategies.
"""
from langgraph.graph import StateGraph, START, END

from app.core.qtype_state import QTypeMorphState
from app.core.qtype_enums import QType
from app.core.enums import ValidationStatus
from app.core.config import settings

from app.nodes.qtype_analyze import qtype_analyze_question
from app.nodes.qtype_calibrate import qtype_calibrate_difficulty
from app.nodes.qtype_router import qtype_route_strategy, dispatch_qtype_strategy
from app.nodes.qtype_validator import qtype_validate_output
from app.nodes.qtype_post_process import qtype_post_process

# FIB nodes
from app.nodes.morph_fib import (
    morph_fib_rephrase, morph_fib_contextual,
    morph_fib_difficulty, morph_fib_multblank,
)
# Short nodes
from app.nodes.morph_short import (
    morph_short_rephrase, morph_short_contextual,
    morph_short_difficulty, morph_short_keyword_shift,
)
# MSQ nodes
from app.nodes.morph_msq import (
    morph_msq_rephrase, morph_msq_distractor,
    morph_msq_difficulty, morph_msq_contextual,
    morph_msq_partial_rules, morph_msq_to_mcq,
)
# Numerical nodes
from app.nodes.morph_numerical import (
    morph_numerical_rephrase, morph_numerical_contextual,
    morph_numerical_values, morph_numerical_units,
    morph_numerical_difficulty,
)
# Long nodes
from app.nodes.morph_long import (
    morph_long_rephrase, morph_long_contextual,
    morph_long_difficulty, morph_long_focus_shift,
)

ALL_MORPH_NODES = [
    "morph_fib_rephrase", "morph_fib_contextual",
    "morph_fib_difficulty", "morph_fib_multblank",
    "morph_short_rephrase", "morph_short_contextual",
    "morph_short_difficulty", "morph_short_keyword_shift",
    "morph_msq_rephrase", "morph_msq_distractor",
    "morph_msq_difficulty", "morph_msq_contextual",
    "morph_msq_partial_rules", "morph_msq_to_mcq",
    "morph_numerical_rephrase", "morph_numerical_contextual",
    "morph_numerical_values", "morph_numerical_units",
    "morph_numerical_difficulty",
    "morph_long_rephrase", "morph_long_contextual",
    "morph_long_difficulty", "morph_long_focus_shift",
]

NODE_FN_MAP = {
    "morph_fib_rephrase":        morph_fib_rephrase,
    "morph_fib_contextual":      morph_fib_contextual,
    "morph_fib_difficulty":      morph_fib_difficulty,
    "morph_fib_multblank":       morph_fib_multblank,
    "morph_short_rephrase":      morph_short_rephrase,
    "morph_short_contextual":    morph_short_contextual,
    "morph_short_difficulty":    morph_short_difficulty,
    "morph_short_keyword_shift": morph_short_keyword_shift,
    "morph_msq_rephrase":        morph_msq_rephrase,
    "morph_msq_distractor":      morph_msq_distractor,
    "morph_msq_difficulty":      morph_msq_difficulty,
    "morph_msq_contextual":      morph_msq_contextual,
    "morph_msq_partial_rules":   morph_msq_partial_rules,
    "morph_msq_to_mcq":          morph_msq_to_mcq,
    "morph_numerical_rephrase":   morph_numerical_rephrase,
    "morph_numerical_contextual": morph_numerical_contextual,
    "morph_numerical_values":     morph_numerical_values,
    "morph_numerical_units":      morph_numerical_units,
    "morph_numerical_difficulty": morph_numerical_difficulty,
    "morph_long_rephrase":       morph_long_rephrase,
    "morph_long_contextual":     morph_long_contextual,
    "morph_long_difficulty":     morph_long_difficulty,
    "morph_long_focus_shift":    morph_long_focus_shift,
}


def qtype_retry_morph(state: QTypeMorphState) -> dict:
    retry_count = state.get("retry_count", 0) + 1
    report      = state.get("validation_report", {})
    print(
        f"[qtype_retry] attempt={retry_count}/{settings.MAX_RETRIES} "
        f"reasons={report.get('failure_reasons', [])}"
    )
    return {"retry_count": retry_count, "validation_report": None}


def qtype_route_after_validation(state: QTypeMorphState) -> str:
    report      = state.get("validation_report", {})
    retry_count = state.get("retry_count", 0)
    if report.get("status") == ValidationStatus.PASS:
        return "qtype_post_process"
    if retry_count < settings.MAX_RETRIES:
        return "qtype_retry_morph"
    print(f"[qtype_edge] Max retries reached. Forwarding to post_process.")
    return "qtype_post_process"


def build_qtype_graph():
    builder = StateGraph(QTypeMorphState)

    # Orchestration nodes
    builder.add_node("qtype_analyze_question",    qtype_analyze_question)
    builder.add_node("qtype_calibrate_difficulty", qtype_calibrate_difficulty)
    builder.add_node("qtype_route_strategy",       qtype_route_strategy)
    builder.add_node("qtype_validate_output",      qtype_validate_output)
    builder.add_node("qtype_retry_morph",          qtype_retry_morph)
    builder.add_node("qtype_post_process",         qtype_post_process)

    # All morph nodes
    for node_name, fn in NODE_FN_MAP.items():
        builder.add_node(node_name, fn)

    # Linear edges
    builder.add_edge(START, "qtype_analyze_question")
    builder.add_edge("qtype_analyze_question",     "qtype_calibrate_difficulty")
    builder.add_edge("qtype_calibrate_difficulty", "qtype_route_strategy")

    # Fan-out via Send API
    builder.add_conditional_edges(
        "qtype_route_strategy",
        dispatch_qtype_strategy,
        ALL_MORPH_NODES,
    )

    # Fan-in: all morph nodes → validator
    for node_name in ALL_MORPH_NODES:
        builder.add_edge(node_name, "qtype_validate_output")

    # Conditional after validation
    builder.add_conditional_edges(
        "qtype_validate_output",
        qtype_route_after_validation,
        {"qtype_post_process": "qtype_post_process", "qtype_retry_morph": "qtype_retry_morph"},
    )

    builder.add_edge("qtype_retry_morph",  "qtype_route_strategy")
    builder.add_edge("qtype_post_process", END)

    return builder.compile()


qtype_graph = build_qtype_graph()