"""
app/nodes/qtype_analyze.py
───────────────────────────
Unified analyze node — works for all 5 question types.
Extracts concept, Bloom level, topic tags, and answer structure.

Reads  : input (any QInput type), qtype
Writes : analysis_result, trace_id, retry_count
"""
from app.core.qtype_state import QTypeMorphState, QTypeAnalysisResult
from app.core.qtype_enums import QType
from app.core.enums import BloomLevel
from app.llm.providers import invoke_with_fallback
from app.llm.qtype_prompts import QTYPE_ANALYZE_PROMPT
from app.utils.json_parser import parse_llm_json
from app.utils.trace import generate_trace_id


def _analyze_bloom_heuristic(question: str, llm_bloom: BloomLevel) -> BloomLevel:
    """
    Validate/enhance LLM bloom analysis using heuristics.
    Upgrades overly-conservative REMEMBER assessments based on question complexity.
    """
    q_lower = question.lower()
    
    # Keywords that suggest higher Bloom levels
    analyze_keywords = {"analyze", "compare", "distinguish", "criticize", "interpret", "examine"}
    evaluate_keywords = {"evaluate", "assess", "judge", "justify", "defend", "critique"}
    apply_keywords = {"apply", "solve", "calculate", "demonstrate", "use", "implement", "construct"}
    understand_keywords = {"explain", "describe", "classify", "identify", "summarize", "discuss"}
    
    # Count keyword occurrences
    q_tokens = set(q_lower.split())
    has_analyze = any(kw in q_lower for kw in analyze_keywords)
    has_evaluate = any(kw in q_lower for kw in evaluate_keywords)
    has_apply = any(kw in q_lower for kw in apply_keywords)
    has_understand = any(kw in q_lower for kw in understand_keywords)
    
    # If LLM said REMEMBER but question has higher-level indicators, upgrade
    if llm_bloom == BloomLevel.REMEMBER:
        if has_evaluate:
            return BloomLevel.EVALUATE
        if has_analyze:
            return BloomLevel.ANALYZE
        if has_apply:
            return BloomLevel.APPLY
        if has_understand:
            return BloomLevel.UNDERSTAND
        # Check complexity: questions with multiple-part requirements or nuance
        if len(question) > 100 and any(phrase in q_lower for phrase in ["which", "select all", "multiple"]):
            return BloomLevel.UNDERSTAND
    
    # If LLM said UNDERSTAND but has evaluation keywords, upgrade
    if llm_bloom == BloomLevel.UNDERSTAND and has_evaluate:
        return BloomLevel.EVALUATE
    
    # If LLM said APPLY but has evaluation keywords, upgrade
    if llm_bloom == BloomLevel.APPLY and has_evaluate:
        return BloomLevel.EVALUATE
    
    return llm_bloom


def qtype_analyze_question(state: QTypeMorphState) -> dict:
    inp   = state["input"]
    qtype = state["qtype"]

    prompt = QTYPE_ANALYZE_PROMPT.format_messages(
        section=inp.section,
        question=inp.question,
        qtype=qtype.value,
    )

    raw = invoke_with_fallback(prompt)

    try:
        data = parse_llm_json(raw)
        llm_bloom = BloomLevel(data.get("bloom_level", "apply"))
        
        # Apply heuristic enhancement
        final_bloom = _analyze_bloom_heuristic(inp.question, llm_bloom)
        if final_bloom != llm_bloom:
            print(f"[qtype_analyze] Bloom upgraded: {llm_bloom.value} -> {final_bloom.value}")
        
        analysis: QTypeAnalysisResult = {
            "qtype":            QType(data.get("qtype", qtype.value)),
            "concept":          data.get("concept", "general"),
            "bloom_level":      final_bloom,
            "topic_tags":       data.get("topic_tags", [inp.section]),
            "answer_structure": data.get("answer_structure", "free_text"),
            "key_terms":        data.get("key_terms", []),
        }
    except Exception as e:
        print(f"[qtype_analyze] Parse error: {e}. Using defaults.")
        analysis: QTypeAnalysisResult = {
            "qtype":            qtype,
            "concept":          "general",
            "bloom_level":      BloomLevel.APPLY,
            "topic_tags":       [inp.section],
            "answer_structure": "free_text",
            "key_terms":        [],
        }

    final_bloom_val = analysis['bloom_level'].value
    print(f"[qtype_analyze] qtype={qtype.value} concept={analysis['concept']} bloom={final_bloom_val}")

    return {
        "trace_id":         generate_trace_id(qtype.value[:3]),
        "analysis_result":  analysis,
        "retry_count":      0,
        "morphed_variants": [],
    }