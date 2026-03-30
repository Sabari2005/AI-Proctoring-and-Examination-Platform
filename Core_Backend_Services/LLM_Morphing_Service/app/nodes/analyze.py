"""
analyze_question node
─────────────────────
First node in the graph. Sends the question to the LLM and extracts:
  - concept         : what is being tested
  - formula         : the underlying logic/formula
  - key_values      : important numeric values
  - bloom_level     : Bloom taxonomy level
  - topic_tags      : 2-4 topic labels

Reads from state  : input (MorphInput)
Writes to state   : analysis_result, trace_id
"""
from app.core.state import MorphState, AnalysisResult
from app.core.enums import BloomLevel
from app.llm.providers import invoke_with_fallback
from app.llm.prompts import ANALYZE_PROMPT
from app.utils.json_parser import parse_llm_json
from app.utils.trace import generate_trace_id


def analyze_question(state: MorphState) -> dict:
    inp = state["input"]

    # Generate a trace ID for this full run
    trace_id = generate_trace_id()

    prompt = ANALYZE_PROMPT.format_messages(
        section=inp.section,
        question=inp.question,
        options=", ".join(inp.options),
        correct_answer=inp.correct_answer,
    )

    raw = invoke_with_fallback(prompt)

    try:
        data = parse_llm_json(raw)
        analysis: AnalysisResult = {
            "concept":    data.get("concept", "general"),
            "formula":    data.get("formula", ""),
            "key_values": data.get("key_values", {}),
            "bloom_level": BloomLevel(data.get("bloom_level", "apply")),
            "topic_tags": data.get("topic_tags", [inp.section]),
        }
    except Exception as e:
        # Graceful fallback — analysis is non-critical
        print(f"[analyze_question] JSON parse failed: {e}. Using defaults.")
        analysis: AnalysisResult = {
            "concept":    "general",
            "formula":    "",
            "key_values": {},
            "bloom_level": BloomLevel.APPLY,
            "topic_tags": [inp.section],
        }

    return {
        "trace_id": trace_id,
        "analysis_result": analysis,
        "retry_count": 0,
        "morphed_variants": [],
    }