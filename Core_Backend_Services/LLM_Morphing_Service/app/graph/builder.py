"""
graph/builder.py
─────────────────
Assembles the full LangGraph StateGraph for LLM question morphing.

Graph topology:
  START
    → analyze_question
    → calibrate_difficulty
    → route_morph_strategy        (conditional fan-out via Send API)
        ↓ parallel branches ↓
        morph_rephrase
        morph_contextual
        morph_distractor
        morph_structural
        morph_difficulty
        ↓ fan-in ↓
    → validate_output
        ├─ pass  → post_process → END
        └─ fail  → retry_morph  → route_morph_strategy (loop)
"""
from langgraph.graph import StateGraph, START, END

from app.core.state import MorphState
from app.nodes import (
    analyze_question,
    calibrate_difficulty,
    route_morph_strategy,
    dispatch_morph_strategy,
    morph_rephrase,
    morph_contextual,
    morph_distractor,
    morph_structural,
    morph_difficulty,
    validate_output,
    retry_morph,
    post_process,
)
from app.graph.edges import route_after_validation, route_after_retry


def build_morph_graph():
    """
    Build and compile the full morphing graph.
    Returns a compiled LangGraph runnable.
    """
    builder = StateGraph(MorphState)

    # ── Register all nodes ───────────────────────────────────────────────
    builder.add_node("analyze_question",     analyze_question)
    builder.add_node("calibrate_difficulty", calibrate_difficulty)
    builder.add_node("route_morph_strategy", route_morph_strategy)
    builder.add_node("morph_rephrase",       morph_rephrase)
    builder.add_node("morph_contextual",     morph_contextual)
    builder.add_node("morph_distractor",     morph_distractor)
    builder.add_node("morph_structural",     morph_structural)
    builder.add_node("morph_difficulty",     morph_difficulty)
    builder.add_node("validate_output",      validate_output)
    builder.add_node("retry_morph",          retry_morph)
    builder.add_node("post_process",         post_process)

    # ── Linear edges (always-run) ────────────────────────────────────────
    builder.add_edge(START,               "analyze_question")
    builder.add_edge("analyze_question",  "calibrate_difficulty")
    builder.add_edge("calibrate_difficulty", "route_morph_strategy")

    # ── Fan-out: router uses Send() API → conditional_edge ───────────────
    # route_morph_strategy returns list[Send] so we use add_conditional_edges
    # with the function itself as the condition
    builder.add_conditional_edges(
        "route_morph_strategy",
        dispatch_morph_strategy,        # returns list[Send] for parallel dispatch
        [                               # all possible destination nodes
            "morph_rephrase",
            "morph_contextual",
            "morph_distractor",
            "morph_structural",
            "morph_difficulty",
        ],
    )

    # ── Fan-in: all morph nodes → validate ───────────────────────────────
    for morph_node in [
        "morph_rephrase",
        "morph_contextual",
        "morph_distractor",
        "morph_structural",
        "morph_difficulty",
    ]:
        builder.add_edge(morph_node, "validate_output")

    # ── Conditional: validation result ───────────────────────────────────
    builder.add_conditional_edges(
        "validate_output",
        route_after_validation,
        {
            "post_process": "post_process",
            "retry_morph":  "retry_morph",
        },
    )

    # ── Retry loop back to router ─────────────────────────────────────────
    builder.add_edge("retry_morph", "route_morph_strategy")

    # ── Terminal ──────────────────────────────────────────────────────────
    builder.add_edge("post_process", END)

    return builder.compile()


# Module-level compiled graph — import this everywhere
morph_graph = build_morph_graph()