"""
app/nodes/qtype_calibrate.py
─────────────────────────────
Pure logic node — no LLM call.
Maps difficulty 1-5 → Bloom level for all question types.
"""
from app.core.qtype_state import QTypeMorphState
from app.core.enums import DifficultyLevel, BloomLevel

DIFFICULTY_TO_BLOOM = {
    DifficultyLevel.VERY_EASY: BloomLevel.REMEMBER,
    DifficultyLevel.EASY:      BloomLevel.UNDERSTAND,
    DifficultyLevel.MEDIUM:    BloomLevel.APPLY,
    DifficultyLevel.HARD:      BloomLevel.ANALYZE,
    DifficultyLevel.VERY_HARD: BloomLevel.EVALUATE,
}

def qtype_calibrate_difficulty(state: QTypeMorphState) -> dict:
    inp    = state["input"]
    config = inp.morph_config
    difficulty_input_provided = bool(state.get("difficulty_input_provided", True))

    # If target_difficulty is explicitly provided in input JSON, always honor it.
    if getattr(config, "target_difficulty", None) is not None:
        difficulty_target = config.target_difficulty
    else:
        difficulty_target = inp.difficulty

    bloom_target = getattr(config, "bloom_target", None) or DIFFICULTY_TO_BLOOM[difficulty_target]

    if difficulty_input_provided:
        original_display = str(inp.difficulty.value)
    else:
        original_display = f"auto(default={inp.difficulty.value})"

    print(
        f"[qtype_calibrate] type={state['qtype'].value} "
        f"original={original_display} → target={difficulty_target.value} "
        f"bloom={bloom_target.value}"
    )

    return {
        "difficulty_target": difficulty_target,
        "bloom_target":      bloom_target,
    }