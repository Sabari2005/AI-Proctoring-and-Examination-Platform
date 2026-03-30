"""
calibrate_difficulty node
──────────────────────────
Pure logic node — no LLM call.
Maps the requested target_difficulty (1-5) to a Bloom level and sets
difficulty_target + bloom_target in state so morph nodes know what to aim for.

Reads from state  : input.difficulty, input.morph_config, analysis_result
Writes to state   : difficulty_target, bloom_target
"""
from app.core.state import MorphState
from app.core.enums import DifficultyLevel, BloomLevel, MorphStrategy


# Maps difficulty level (1-5) → Bloom taxonomy level
DIFFICULTY_TO_BLOOM = {
    DifficultyLevel.VERY_EASY: BloomLevel.REMEMBER,
    DifficultyLevel.EASY:      BloomLevel.UNDERSTAND,
    DifficultyLevel.MEDIUM:    BloomLevel.APPLY,
    DifficultyLevel.HARD:      BloomLevel.ANALYZE,
    DifficultyLevel.VERY_HARD: BloomLevel.EVALUATE,
}


def calibrate_difficulty(state: MorphState) -> dict:
    inp = state["input"]
    config = inp.morph_config
    analysis = state.get("analysis_result", {})

    # Determine target difficulty
    if MorphStrategy.DIFFICULTY in config.strategies and config.target_difficulty:
        difficulty_target = config.target_difficulty
    else:
        # Keep original difficulty for non-difficulty morphs
        difficulty_target = inp.difficulty

    bloom_target = DIFFICULTY_TO_BLOOM[difficulty_target]

    print(
        f"[calibrate] Original difficulty={inp.difficulty.value}, "
        f"Target={difficulty_target.value}, Bloom={bloom_target.value}"
    )

    return {
        "difficulty_target": difficulty_target,
        "bloom_target": bloom_target,
    }