"""
app/nodes/qtype_router.py
──────────────────────────
Conditional edge — dispatches each strategy as a parallel Send().
Maps strategy string → node name for all 5 question types.
"""
from langgraph.types import Send
from app.core.qtype_state import QTypeMorphState

STRATEGY_TO_NODE = {
    # FIB
    "fib_rephrase":   "morph_fib_rephrase",
    "fib_contextual": "morph_fib_contextual",
    "fib_difficulty": "morph_fib_difficulty",
    "fib_multblank":  "morph_fib_multblank",
    # Short
    "short_rephrase":      "morph_short_rephrase",
    "short_contextual":    "morph_short_contextual",
    "short_difficulty":    "morph_short_difficulty",
    "short_keyword_shift": "morph_short_keyword_shift",
    # MSQ
    "msq_rephrase":   "morph_msq_rephrase",
    "msq_distractor": "morph_msq_distractor",
    "msq_difficulty": "morph_msq_difficulty",
    "msq_contextual": "morph_msq_contextual",
    "msq_partial_rules": "morph_msq_partial_rules",
    "msq_to_mcq": "morph_msq_to_mcq",
    # Numerical
    "numerical_rephrase":   "morph_numerical_rephrase",
    "numerical_contextual": "morph_numerical_contextual",
    "numerical_values":     "morph_numerical_values",
    "numerical_units":      "morph_numerical_units",
    "numerical_difficulty": "morph_numerical_difficulty",
    # Long
    "long_rephrase":    "morph_long_rephrase",
    "long_contextual":  "morph_long_contextual",
    "long_difficulty":  "morph_long_difficulty",
    "long_focus_shift": "morph_long_focus_shift",
}


def qtype_route_strategy(state: QTypeMorphState) -> dict:
    # Routing is performed by dispatch_qtype_strategy via conditional edges.
    return {}


def dispatch_qtype_strategy(state: QTypeMorphState) -> list[Send]:
    strategies = state["input"].morph_config.strategies
    sends = []
    for strategy in strategies:
        strategy_key = strategy.value if hasattr(strategy, "value") else str(strategy)
        node = STRATEGY_TO_NODE.get(strategy_key)
        if node:
            sends.append(Send(node, {**state, "current_strategy": strategy_key}))
        else:
            print(f"[qtype_router] Unknown strategy: {strategy_key}, skipping.")
    print(f"[qtype_router] Dispatching {len(sends)} strategy/strategies: {[s.value if hasattr(s, 'value') else str(s) for s in strategies]}")
    return sends