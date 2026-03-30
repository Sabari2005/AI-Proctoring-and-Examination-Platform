"""
app/graph/coding_builder.py
────────────────────────────
Assembles the coding question morphing StateGraph.

Topology (mirrors the MCQ graph, different nodes):
  START
    → coding_analyze_question
    → coding_calibrate_difficulty
    → coding_route_strategy          (conditional fan-out via Send API)
        ↓ parallel ↓
        morph_code_rephrase
        morph_code_contextual
        morph_code_difficulty
        morph_code_constraint
        morph_code_tcgen
        morph_code_tcscale
        ↓ fan-in ↓
    → coding_validate_output
        ├─ pass → coding_post_process → END
        └─ fail → coding_retry       → coding_route_strategy (loop)
"""
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send

from app.core.coding_state import CodingMorphState
from app.core.enums import ValidationStatus
from app.core.config import settings

from app.nodes.coding_analyze import coding_analyze_question
from app.nodes.coding_calibrate import coding_calibrate_difficulty
from app.nodes.coding_router import coding_route_strategy, dispatch_coding_strategy
from app.nodes.morph_code_rephrase import morph_code_rephrase
from app.nodes.morph_code_contextual import morph_code_contextual
from app.nodes.morph_code_difficulty import morph_code_difficulty
from app.nodes.morph_code_constraint import morph_code_constraint
from app.nodes.morph_code_tcgen import morph_code_tcgen
from app.nodes.morph_code_tcscale import morph_code_tcscale
from app.nodes.coding_validator import coding_validate_output
from app.nodes.coding_post_process import coding_post_process


# ── Retry node (inline — same logic as MCQ retry) ────────────────────────────

def coding_retry_morph(state: CodingMorphState) -> dict:
    retry_count = state.get("retry_count", 0) + 1
    report      = state.get("validation_report", {})
    variants    = state.get("morphed_variants", [])

    print(
        f"[coding_retry] attempt={retry_count}/{settings.MAX_RETRIES} "
        f"reasons={report.get('failure_reasons', [])}"
    )

    return {
        "retry_count":       retry_count,
        "validation_report": None,
    }


# ── Conditional edge: after validation ───────────────────────────────────────

def coding_route_after_validation(state: CodingMorphState) -> str:
    report      = state.get("validation_report", {})
    retry_count = state.get("retry_count", 0)

    if report.get("status") == ValidationStatus.PASS:
        return "coding_post_process"

    if retry_count < settings.MAX_RETRIES:
        return "coding_retry_morph"

    print(f"[coding_edge] Max retries reached. Forwarding to post_process.")
    return "coding_post_process"


# ── Graph assembly ────────────────────────────────────────────────────────────

def build_coding_morph_graph():
    builder = StateGraph(CodingMorphState)

    builder.add_node("coding_analyze_question",    coding_analyze_question)
    builder.add_node("coding_calibrate_difficulty", coding_calibrate_difficulty)
    builder.add_node("coding_route_strategy",       coding_route_strategy)
    builder.add_node("morph_code_rephrase",         morph_code_rephrase)
    builder.add_node("morph_code_contextual",       morph_code_contextual)
    builder.add_node("morph_code_difficulty",       morph_code_difficulty)
    builder.add_node("morph_code_constraint",       morph_code_constraint)
    builder.add_node("morph_code_tcgen",            morph_code_tcgen)
    builder.add_node("morph_code_tcscale",          morph_code_tcscale)
    builder.add_node("coding_validate_output",      coding_validate_output)
    builder.add_node("coding_retry_morph",          coding_retry_morph)
    builder.add_node("coding_post_process",         coding_post_process)

    # Linear edges
    builder.add_edge(START,                          "coding_analyze_question")
    builder.add_edge("coding_analyze_question",      "coding_calibrate_difficulty")
    builder.add_edge("coding_calibrate_difficulty",  "coding_route_strategy")

    # Fan-out via Send API
    builder.add_conditional_edges(
        "coding_route_strategy",
        dispatch_coding_strategy,
        [
            "morph_code_rephrase",
            "morph_code_contextual",
            "morph_code_difficulty",
            "morph_code_constraint",
            "morph_code_tcgen",
            "morph_code_tcscale",
        ],
    )

    # Fan-in: all morph nodes → validator
    for node in [
        "morph_code_rephrase", "morph_code_contextual", "morph_code_difficulty",
        "morph_code_constraint", "morph_code_tcgen", "morph_code_tcscale",
    ]:
        builder.add_edge(node, "coding_validate_output")

    # Conditional after validation
    builder.add_conditional_edges(
        "coding_validate_output",
        coding_route_after_validation,
        {
            "coding_post_process": "coding_post_process",
            "coding_retry_morph":  "coding_retry_morph",
        },
    )

    # Retry loop
    builder.add_edge("coding_retry_morph", "coding_route_strategy")

    # Terminal
    builder.add_edge("coding_post_process", END)

    return builder.compile()


coding_morph_graph = build_coding_morph_graph()