from typing import Dict


def estimate_complexities(source_code: str) -> Dict[str, str]:
    """Best-effort complexity estimation from code shape heuristics."""
    code = source_code or ""
    lowered = code.lower()

    nested_loop_markers = ["for", "while"]
    loop_count = sum(lowered.count(marker) for marker in nested_loop_markers)

    if "sort(" in lowered or ".sort(" in lowered or "sorted(" in lowered:
        time_complexity = "O(n log n)"
    elif loop_count >= 3:
        time_complexity = "O(n^3)"
    elif loop_count == 2:
        time_complexity = "O(n^2)"
    elif loop_count == 1:
        time_complexity = "O(n)"
    elif "binarysearch" in lowered or "mid =" in lowered:
        time_complexity = "O(log n)"
    else:
        time_complexity = "O(1)"

    if any(token in lowered for token in ("dict", "map", "set", "list", "vector", "array")):
        space_complexity = "O(n)"
    else:
        space_complexity = "O(1)"

    return {
        "estimated_time_complexity": time_complexity,
        "estimated_space_complexity": space_complexity,
    }
