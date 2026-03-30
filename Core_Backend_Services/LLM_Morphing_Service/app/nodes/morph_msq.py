"""
app/nodes/morph_msq.py
───────────────────────
All Multiple Select Question morph nodes:
  morph_msq_rephrase   — reword, options unchanged
  morph_msq_distractor — replace wrong options with traps
  morph_msq_difficulty — add/remove correct answers
  morph_msq_contextual — new domain, same correct set structure
"""
from app.core.qtype_state import QTypeMorphState
from app.core.qtype_schemas import MorphedMSQ
from app.core.qtype_enums import MSQMorphStrategy
from app.llm.providers import invoke_with_fallback
from app.llm.qtype_prompts import (
    MSQ_REPHRASE_PROMPT, MSQ_DISTRACTOR_PROMPT,
    MSQ_DIFFICULTY_PROMPT, MSQ_CONTEXTUAL_PROMPT,
)
from app.utils.json_parser import parse_llm_json
from app.utils.similarity import compute_similarity
import re


DOMAIN_STOPWORDS = {
    "which", "following", "select", "apply", "what", "when", "where", "why", "how",
    "built", "into", "with", "from", "that", "this", "these", "those", "than",
    "question", "choose", "correct", "answer", "answers", "option", "options",
    "all", "are", "for", "and", "the", "your", "about", "data", "types", "type",
}


def _salient_terms(text: str) -> set[str]:
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9_+-]*", text.lower())
    return {t for t in tokens if len(t) >= 4 and t not in DOMAIN_STOPWORDS}


def _domain_overlap_ratio(source_text: str, candidate_text: str) -> float:
    source_terms = _salient_terms(source_text)
    if not source_terms:
        return 1.0
    candidate_terms = _salient_terms(candidate_text)
    return len(source_terms & candidate_terms) / float(len(source_terms))


def _build_msq(
    state, new_q, new_opts, new_correct,
    strategy, answer_changed, explanation,
    partial_credit=None, penalty_for_wrong=None,
) -> dict:
    inp   = state["input"]
    score = compute_similarity(inp.question, new_q)
    flags = []
    # All correct answers must appear in options
    missing = [a for a in new_correct if a not in new_opts]
    if missing:
        flags.append(f"correct_answers_missing_from_options: {missing}")
        new_opts = new_opts + missing   # safety patch
    if len(new_correct) < 2:
        flags.append("too_few_correct_answers")
    if score < 0.50 and not answer_changed:
        flags.append("meaning_drift")

    variant = MorphedMSQ(
        question=new_q,
        options=new_opts,
        correct_answers=new_correct,
        partial_credit=inp.partial_credit if partial_credit is None else bool(partial_credit),
        penalty_for_wrong=inp.penalty_for_wrong if penalty_for_wrong is None else bool(penalty_for_wrong),
        morph_type=strategy,
        difficulty_actual=state.get("difficulty_target", inp.difficulty),
        semantic_score=round(score, 4),
        answer_changed=answer_changed,
        quality_flags=flags,
        explanation=explanation,
    )
    print(f"[{strategy.value}] semantic={score:.3f} correct_count={len(new_correct)} flags={flags}")
    return {"morphed_variants": [variant]}


def morph_msq_rephrase(state: QTypeMorphState) -> dict:
    inp      = state["input"]
    analysis = state.get("analysis_result", {})
    raw = invoke_with_fallback(MSQ_REPHRASE_PROMPT.format_messages(
        question=inp.question,
        options=", ".join(inp.options),
        correct_answers=", ".join(inp.correct_answers),
        concept=analysis.get("concept", ""),
    ))
    try:
        d     = parse_llm_json(raw)
        new_q = d.get("question", inp.question)
    except Exception as e:
        print(f"[msq_rephrase] Parse error: {e}")
        new_q = inp.question

    return _build_msq(
        state, new_q, inp.options, inp.correct_answers,
        MSQMorphStrategy.REPHRASE, False,
        "Question rephrased. Options and correct answers unchanged.",
    )


def morph_msq_distractor(state: QTypeMorphState) -> dict:
    inp      = state["input"]
    analysis = state.get("analysis_result", {})
    target   = state.get("difficulty_target", inp.difficulty)
    bloom    = state.get("bloom_target", None)
    raw = invoke_with_fallback(MSQ_DISTRACTOR_PROMPT.format_messages(
        question=inp.question,
        options=", ".join(inp.options),
        correct_answers=", ".join(inp.correct_answers),
        concept=analysis.get("concept", ""),
        current_level=inp.difficulty.value,
        target_level=target.value,
        bloom_target=(bloom.value if hasattr(bloom, "value") else str(bloom or "")),
    ))
    try:
        d        = parse_llm_json(raw)
        new_opts = d.get("options", inp.options)
        if not isinstance(new_opts, list):
            new_opts = inp.options
    except Exception as e:
        print(f"[msq_distractor] Parse error: {e}")
        new_opts = inp.options

    return _build_msq(
        state, inp.question, new_opts, inp.correct_answers,
        MSQMorphStrategy.DISTRACTOR, False,
        "Wrong options replaced with deceptive near-correct distractors.",
    )


def morph_msq_difficulty(state: QTypeMorphState) -> dict:
    inp       = state["input"]
    analysis  = state.get("analysis_result", {})
    target    = state.get("difficulty_target", inp.difficulty)
    direction = "harder" if target.value > inp.difficulty.value else "easier"
    raw = invoke_with_fallback(MSQ_DIFFICULTY_PROMPT.format_messages(
        question=inp.question,
        options=", ".join(inp.options),
        correct_answers=", ".join(inp.correct_answers),
        concept=analysis.get("concept", ""),
        current_level=inp.difficulty.value,
        target_level=target.value,
        direction=direction,
    ))
    try:
        d           = parse_llm_json(raw)
        new_q       = d.get("question", inp.question)
        new_opts    = d.get("options", inp.options)
        new_correct = d.get("correct_answers", inp.correct_answers)
        if not isinstance(new_opts, list):
            new_opts = inp.options
        if not isinstance(new_correct, list):
            new_correct = inp.correct_answers
    except Exception as e:
        print(f"[msq_difficulty] Parse error: {e}")
        new_q, new_opts, new_correct = inp.question, inp.options, inp.correct_answers

    answer_changed = (
        new_q != inp.question
        or new_opts != inp.options
        or new_correct != inp.correct_answers
    )
    explanation = (
        f"Difficulty shifted {direction}: answer set/options adjusted."
        if answer_changed
        else "Difficulty strategy produced no valid structural change; retained original content."
    )

    return _build_msq(
        state, new_q, new_opts, new_correct,
        MSQMorphStrategy.DIFFICULTY, answer_changed,
        explanation,
    )


def morph_msq_contextual(state: QTypeMorphState) -> dict:
    inp      = state["input"]
    analysis = state.get("analysis_result", {})
    raw = invoke_with_fallback(MSQ_CONTEXTUAL_PROMPT.format_messages(
        question=inp.question,
        options=", ".join(inp.options),
        correct_answers=", ".join(inp.correct_answers),
        concept=analysis.get("concept", ""),
    ))
    try:
        d     = parse_llm_json(raw)
        new_q = d.get("question", inp.question)
    except Exception as e:
        print(f"[msq_contextual] Parse error: {e}")
        new_q = inp.question

    # Guard against subject-domain drift for any topic by requiring domain-term overlap.
    overlap = _domain_overlap_ratio(inp.question, str(new_q))
    if overlap < 0.34:
        print(
            f"[msq_contextual] Domain drift detected (overlap={overlap:.2f}); "
            "restoring original question stem."
        )
        new_q = inp.question

    answer_changed = new_q != inp.question

    return _build_msq(
        state, new_q, inp.options, inp.correct_answers,
        MSQMorphStrategy.CONTEXTUAL, answer_changed,
        "Question stem contextualized while preserving original domain, options, and correct answers.",
    )


def morph_msq_partial_rules(state: QTypeMorphState) -> dict:
    inp    = state["input"]
    target = state.get("difficulty_target", inp.difficulty)

    # Policy shift only: keep question/options/answers intact; adjust scoring strictness.
    if target.value >= 4:
        partial_credit = False
        penalty_for_wrong = True
        explanation = "Scoring policy tightened for higher target difficulty (no partial credit, penalty enabled)."
    else:
        partial_credit = True
        penalty_for_wrong = False
        explanation = "Scoring policy relaxed for lower target difficulty (partial credit enabled, no wrong-option penalty)."

    return _build_msq(
        state, inp.question, inp.options, inp.correct_answers,
        MSQMorphStrategy.PARTIAL_RULES, False,
        explanation,
        partial_credit=partial_credit,
        penalty_for_wrong=penalty_for_wrong,
    )


def morph_msq_to_mcq(state: QTypeMorphState) -> dict:
    inp = state["input"]

    # This pipeline emits MorphedMSQ outputs (min 2 correct answers), so we emulate
    # conversion by making the item more single-focus while staying schema-valid.
    if len(inp.correct_answers) <= 2:
        narrowed_correct = list(inp.correct_answers)
    else:
        narrowed_correct = list(inp.correct_answers[:2])

    explanation = (
        "MCQ-style narrowing applied (reduced correct set) while preserving MSQ schema "
        "requirements for downstream compatibility."
    )

    return _build_msq(
        state, inp.question, inp.options, narrowed_correct,
        MSQMorphStrategy.TO_MCQ, True,
        explanation,
    )