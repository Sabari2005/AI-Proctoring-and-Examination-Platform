"""
coding_calibrate.py
────────────────────
Pure logic node — no LLM call.
Maps difficulty 1-5 to Bloom level and sets targets in state.

Also infers "naive complexity" for stress test generation:
  If best is O(n), naive is O(n²). If best is O(n log n), naive is O(n²), etc.

Reads  : input, analysis_result
Writes : difficulty_target, bloom_target
"""
from app.core.coding_state import CodingMorphState
from app.core.enums import DifficultyLevel, BloomLevel


DIFFICULTY_TO_BLOOM = {
    DifficultyLevel.VERY_EASY: BloomLevel.REMEMBER,
    DifficultyLevel.EASY:      BloomLevel.UNDERSTAND,
    DifficultyLevel.MEDIUM:    BloomLevel.APPLY,
    DifficultyLevel.HARD:      BloomLevel.ANALYZE,
    DifficultyLevel.VERY_HARD: BloomLevel.EVALUATE,
}

# Infer naive complexity (what a brute-force attempt looks like)
NAIVE_COMPLEXITY = {
    "O(1)":          "O(n)",
    "O(log n)":      "O(n)",
    "O(n)":          "O(n²)",
    "O(n log n)":    "O(n²)",
    "O(n²)":         "O(n³)",
    "O(n³)":         "O(n!)",
}


def coding_calibrate_difficulty(state: CodingMorphState) -> dict:
    inp      = state["input"]
    config   = inp.morph_config
    analysis = state.get("analysis_result", {})

    # If target_difficulty is explicitly provided, always honor it.
    if config.target_difficulty:
        difficulty_target = config.target_difficulty
    else:
        difficulty_target = inp.difficulty

    bloom_target = DIFFICULTY_TO_BLOOM[difficulty_target]

    time_complexity = analysis.get("time_complexity", "O(n)")
    naive = NAIVE_COMPLEXITY.get(time_complexity, "O(n²)")

    print(
        f"[coding_calibrate] difficulty={difficulty_target.value} "
        f"bloom={bloom_target.value} "
        f"best_tc={time_complexity} naive={naive}"
    )

    return {
        "difficulty_target": difficulty_target,
        "bloom_target":      bloom_target,
    }