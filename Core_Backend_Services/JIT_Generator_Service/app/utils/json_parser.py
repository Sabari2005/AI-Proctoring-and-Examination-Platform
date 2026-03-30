import json, re


def parse_llm_json(raw: str) -> dict:
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().strip("`").strip()
    start = cleaned.find("{")
    end   = cleaned.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No JSON found in: {raw[:200]}")
    try:
        return json.loads(cleaned[start:end])
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON parse error: {e}\nContent: {cleaned[start:end][:300]}")