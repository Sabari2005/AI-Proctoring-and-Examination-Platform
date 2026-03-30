"""
coding_router.py
─────────────────
Conditional edge — dispatches each coding morph strategy via Send() API.

Reads  : input.morph_config.strategies
Returns: list[Send] for parallel execution
"""
from langgraph.types import Send
from app.core.coding_state import CodingMorphState


CODING_STRATEGY_TO_NODE = {
    "code_rephrase":   "morph_code_rephrase",
    "code_contextual": "morph_code_contextual",
    "code_difficulty": "morph_code_difficulty",
    "code_constraint": "morph_code_constraint",
    "code_tcgen":      "morph_code_tcgen",
    "code_tcscale":    "morph_code_tcscale",
}


def coding_route_strategy(state: CodingMorphState) -> dict:
    """Router node — returns empty dict state update."""
    return {}


def dispatch_coding_strategy(state: CodingMorphState) -> list[Send]:
    """Conditional edge function — returns list[Send] for parallel dispatch."""
    strategies = state["input"].morph_config.strategies
    sends = []

    for strategy in strategies:
        node = CODING_STRATEGY_TO_NODE.get(strategy)
        if node:
            sends.append(Send(node, {**state, "current_strategy": strategy}))
        else:
            print(f"[coding_router] Unknown strategy: {strategy}, skipping.")

    print(f"[coding_router] Dispatching {len(sends)} strategy/strategies: {strategies}")
    return sends