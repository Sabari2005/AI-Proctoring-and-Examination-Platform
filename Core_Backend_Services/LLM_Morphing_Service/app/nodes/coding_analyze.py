"""
coding_analyze.py
──────────────────
First node in the coding morph graph.
Extracts algorithm category, data structures, complexity, and Bloom level.

Reads  : input (CodingMorphInput)
Writes : analysis_result (CodingAnalysisResult), trace_id, retry_count
"""
import json
from app.core.coding_state import CodingMorphState, CodingAnalysisResult
from app.core.enums import BloomLevel
from app.llm.providers import invoke_with_fallback
from app.llm.coding_prompts import CODING_ANALYZE_PROMPT
from app.utils.json_parser import parse_llm_json
from app.utils.trace import generate_trace_id


def coding_analyze_question(state: CodingMorphState) -> dict:
    inp = state["input"]

    # Serialize test cases for the prompt (just show structure, not all values)
    tc_preview = {}
    for name, tc in list(inp.test_cases.items())[:3]:   # show max 3 TCs
        tc_preview[name] = {"input": tc.input, "output": tc.output}

    prompt = CODING_ANALYZE_PROMPT.format_messages(
        section=inp.section,
        question=inp.question,
        test_cases=json.dumps(tc_preview, default=str),
        constraints=inp.constraints.model_dump(),
    )

    raw = invoke_with_fallback(prompt)

    try:
        data = parse_llm_json(raw)
        analysis: CodingAnalysisResult = {
            "algorithm_category": data.get("algorithm_category", "general"),
            "data_structures":    data.get("data_structures", []),
            "time_complexity":    data.get("time_complexity", "O(n)"),
            "space_complexity":   data.get("space_complexity", "O(n)"),
            "bloom_level":        BloomLevel(data.get("bloom_level", "apply")),
            "topic_tags":         data.get("topic_tags", inp.topic_tags),
            "core_logic":         data.get("core_logic", ""),
        }
    except Exception as e:
        print(f"[coding_analyze] Parse error: {e}. Using defaults.")
        analysis: CodingAnalysisResult = {
            "algorithm_category": "general",
            "data_structures":    [],
            "time_complexity":    "O(n)",
            "space_complexity":   "O(n)",
            "bloom_level":        BloomLevel.APPLY,
            "topic_tags":         inp.topic_tags,
            "core_logic":         "",
        }

    print(
        f"[coding_analyze] algorithm={analysis['algorithm_category']} "
        f"time={analysis['time_complexity']} "
        f"bloom={analysis['bloom_level']}"
    )

    return {
        "trace_id":        generate_trace_id("code"),
        "analysis_result": analysis,
        "retry_count":     0,
        "morphed_variants": [],
    }