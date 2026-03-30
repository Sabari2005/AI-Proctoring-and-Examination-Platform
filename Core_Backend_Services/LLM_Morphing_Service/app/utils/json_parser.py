import json
import re


def parse_llm_json(raw: str) -> dict:
    """
    Safely extract and parse JSON from an LLM response.
    Handles cases where the LLM wraps JSON in markdown code fences
    or adds extra explanation text around it.

    Example:
        raw = '```json\\n{"question": "A cyclist..."}\\n```'
        parse_llm_json(raw)  # Returns {"question": "A cyclist..."}
    """
    # Strip markdown fences
    cleaned = re.sub(r"```(?:json)?", "", raw).strip()
    cleaned = cleaned.strip("`").strip()

    # Find the first { ... } block
    start = cleaned.find("{")
    end = cleaned.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No JSON object found in LLM response:\n{raw[:300]}")

    json_str = cleaned[start:end]

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON parse failed: {e}\nRaw content:\n{json_str[:300]}")