"""
route_morph_strategy node
──────────────────────────
The fan-out point. Uses LangGraph's Send() API to dispatch each requested
morph strategy as a parallel branch. All morph nodes run concurrently and
their results are collected via the Annotated[list, operator.add] reducer
in MorphState.morphed_variants.

Reads from state  : input.morph_config.strategies
Returns           : list[Send] — one per strategy
"""
from langgraph.types import Send
from app.core.state import MorphState
from app.core.enums import MorphStrategy


# Maps strategy enum → the node function name in the graph
STRATEGY_TO_NODE = {
    MorphStrategy.REPHRASE:   "morph_rephrase",
    MorphStrategy.CONTEXTUAL: "morph_contextual",
    MorphStrategy.DISTRACTOR: "morph_distractor",
    MorphStrategy.STRUCTURAL: "morph_structural",
    MorphStrategy.DIFFICULTY: "morph_difficulty",
}


def route_morph_strategy(state: MorphState) -> list[Send]:
    """Router node; returns a state update dict."""
    return {}


def dispatch_morph_strategy(state: MorphState) -> list[Send]:
    """
    Called as a conditional edge function.
    Returns a list of Send objects — LangGraph fires all of them in parallel.
    """
    strategies = state["input"].morph_config.strategies

    sends = []
    for strategy in strategies:
        node_name = STRATEGY_TO_NODE.get(strategy)
        if node_name:
            # Each Send carries a copy of state with the active strategy tagged
            sends.append(Send(node_name, {**state, "current_strategy": strategy.value}))
        else:
            print(f"[router] Unknown strategy: {strategy}, skipping.")

    print(f"[router] Dispatching {len(sends)} parallel morph(s): {[s.value for s in strategies]}")
    return sends