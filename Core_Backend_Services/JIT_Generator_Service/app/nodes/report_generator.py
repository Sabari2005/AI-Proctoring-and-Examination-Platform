"""
JIT/app/nodes/report_generator.py
───────────────────────────────────
Generates the final skill assessment report after all questions answered.
"""
from app.core.state import JITGraphState
from app.core.schemas import FinalReport
from app.core.enums import (
    AnswerStatus, BloomLevel, theta_to_skill, DIFFICULTY_TO_BLOOM,
)
from app.llm.providers import invoke_with_fallback
from app.llm.prompts import REPORT_GEN_PROMPT
from app.utils.json_parser import parse_llm_json
from app.utils.session_store import update_session
from app.utils.jit_db_store import persist_final_report


def _normalize_str_list(items) -> list[str]:
    """Coerce mixed LLM list outputs into a clean list[str]."""
    if not isinstance(items, list):
        return []

    normalized: list[str] = []
    for item in items:
        if isinstance(item, str):
            value = item.strip()
            if value:
                normalized.append(value)
            continue

        if isinstance(item, dict):
            # Prefer common text-like keys when the model returns objects.
            for key in ("text", "summary", "recommendation", "strength", "weakness", "title"):
                value = item.get(key)
                if isinstance(value, str) and value.strip():
                    normalized.append(value.strip())
                    break
            else:
                compact = ", ".join(f"{k}: {v}" for k, v in item.items())
                if compact:
                    normalized.append(compact)
            continue

        normalized.append(str(item))

    return normalized


def _compute_subtopic_mastery_from_history(history, sub_topic_queue) -> tuple[dict[str, float], dict[str, int]]:
    """Compute smoothed mastery from attempts only; unseen topics are excluded."""
    prior_weight = 2.0
    prior_mean = 0.5

    attempts: dict[str, int] = {topic: 0 for topic in sub_topic_queue}
    score_sums: dict[str, float] = {topic: 0.0 for topic in sub_topic_queue}

    for record in history:
        topic = record.question.sub_topic or ""
        if topic not in attempts:
            attempts[topic] = 0
            score_sums[topic] = 0.0

        attempts[topic] += 1
        score = max(0.0, min(1.0, float(record.evaluation.score)))
        score_sums[topic] += score

    mastery = {}
    for topic, n_attempts in attempts.items():
        if n_attempts <= 0:
            continue
        smoothed = (score_sums[topic] + prior_weight * prior_mean) / (n_attempts + prior_weight)
        mastery[topic] = round(smoothed * 100.0, 1)

    return mastery, attempts


def report_generator(state: JITGraphState) -> dict:
    session = state["session"]
    history = session.question_history
    config  = session.config

    # ── Basic stats ───────────────────────────────────────────────────────
    correct = sum(1 for r in history if r.evaluation.status == AnswerStatus.CORRECT)
    partial = sum(1 for r in history if r.evaluation.status == AnswerStatus.PARTIAL)
    wrong   = sum(1 for r in history if r.evaluation.status in (
        AnswerStatus.WRONG, AnswerStatus.SKIPPED, AnswerStatus.TIMEOUT
    ))
    total   = len(history)
    accuracy = round((correct + partial * 0.5) / max(total, 1) * 100, 1)

    # ── Theta and skill ───────────────────────────────────────────────────
    theta_final = session.theta
    skill_label = theta_to_skill(theta_final)

    # ── Highest Bloom level consistently demonstrated ─────────────────────
    bloom_order = [
        BloomLevel.REMEMBER, BloomLevel.UNDERSTAND,
        BloomLevel.APPLY, BloomLevel.ANALYZE, BloomLevel.EVALUATE,
    ]
    blooms_reached = session.bloom_levels_reached
    highest_bloom  = BloomLevel.REMEMBER
    for bloom in bloom_order:
        bloom_qs = [b for b in blooms_reached if b == bloom]
        bloom_correct = sum(
            1 for r in history
            if DIFFICULTY_TO_BLOOM[r.question.difficulty] == bloom
            and r.evaluation.status == AnswerStatus.CORRECT
        )
        if bloom_correct >= max(len(bloom_qs) * 0.6, 1):
            highest_bloom = bloom

    # ── Speed profile ─────────────────────────────────────────────────────
    avg_time_ratio = sum(r.evaluation.time_ratio for r in history) / max(total, 1)
    if avg_time_ratio < 0.7:
        speed_profile = "fast"
    elif avg_time_ratio <= 1.2:
        speed_profile = "normal"
    else:
        speed_profile = "slow"

    # ── Sub-topic mastery ─────────────────────────────────────────────────
    # sub_topic_mastery, sub_topic_attempts = _compute_subtopic_mastery_from_history(
    #     history,
    #     session.sub_topic_queue,
    # )
    # result = _compute_subtopic_mastery_from_history(
    #     history,
    #     session.sub_topic_queue or [],
    # )
    # if result is None:
    #     sub_topic_mastery, sub_topic_attempts = {}, {}
    # else:
    #     sub_topic_mastery, sub_topic_attempts = result
    # if not sub_topic_mastery:
    #     # Defensive fallback for unexpected empty history.
    #     sub_topic_mastery = {
    #         k: round(v, 1)
    #         for k, v in session.sub_topic_mastery.items()
    #         if v != 50.0
    #     }
# ── Sub-topic mastery ─────────────────────────────────────────────────
    try:
        _mastery_result = _compute_subtopic_mastery_from_history(
            history,
            session.sub_topic_queue or [],
        )
        sub_topic_mastery, sub_topic_attempts = _mastery_result
    except Exception as _mastery_err:
        print(f"[report_generator] Mastery compute failed: {_mastery_err}. Using fallback.")
        sub_topic_mastery, sub_topic_attempts = {}, {}

    if not sub_topic_mastery:
        # Defensive fallback for unexpected empty history.
        sub_topic_mastery = {
            k: round(v, 1)
            for k, v in (session.sub_topic_mastery or {}).items()
            if v != 50.0
        }
    # ── Strengths and weaknesses ──────────────────────────────────────────
    strengths  = [
        st for st, m in sub_topic_mastery.items()
        if sub_topic_attempts.get(st, 0) >= 2 and m >= 70
    ]
    weaknesses = [
        st for st, m in sub_topic_mastery.items()
        if sub_topic_attempts.get(st, 0) >= 2 and m < 50
    ]

    # ── LLM-generated recommendations ────────────────────────────────────
    try:
        raw  = invoke_with_fallback(REPORT_GEN_PROMPT.format_messages(
            section_topic=config.section_topic,
            total_questions=total,
            accuracy=accuracy,
            theta=theta_final,
            skill_label=skill_label.value,
            subtopic_mastery=sub_topic_mastery,
            trajectory=session.difficulty_trajectory,
            speed_profile=speed_profile,
        ))
        llm_data = parse_llm_json(raw)
        recommendations = _normalize_str_list(llm_data.get("recommendations", []))
        if not strengths:
            strengths = _normalize_str_list(llm_data.get("strengths", []))
        if not weaknesses:
            weaknesses = _normalize_str_list(llm_data.get("weaknesses", []))
    except Exception as e:
        print(f"[report_generator] LLM report error: {e}. Using computed values.")
        recommendations = [
            f"Focus on: {', '.join(weaknesses[:2]) if weaknesses else 'all sub-topics'}",
            f"Practice more {config.question_type.value} type questions.",
        ]

    # ── Question summary ──────────────────────────────────────────────────
    question_summary = [
        {
            "q_num":      r.question.question_number,
            "sub_topic":  r.question.sub_topic,
            "difficulty": r.question.difficulty.value,
            "qtype":      r.question.qtype.value,
            "status":     r.evaluation.status.value,
            "score":      r.evaluation.score,
            "time_ratio": r.evaluation.time_ratio,
        }
        for r in history
    ]

    report = FinalReport(
        session_id=session.session_id,
        candidate_id=config.candidate_id,
        section_topic=config.section_topic,
        total_questions=total,
        correct=correct,
        partial=partial,
        wrong=wrong,
        accuracy=accuracy,
        theta_final=round(theta_final, 3),
        skill_label=skill_label,
        highest_bloom=highest_bloom,
        difficulty_trajectory=session.difficulty_trajectory,
        sub_topic_mastery=sub_topic_mastery,
        sub_topic_attempts={
            topic: count for topic, count in sub_topic_attempts.items() if count > 0
        },
        avg_time_ratio=round(avg_time_ratio, 3),
        speed_profile=speed_profile,
        strengths=strengths,
        weaknesses=weaknesses,
        recommendations=recommendations,
        question_summary=question_summary,
    )

    session.final_report = report.model_dump()
    session.status       = "completed"
    
    # Persist final report to database (jit_section_sessions.final_report)
    try:
        persist_final_report(session.session_id, session.final_report)
        print(f"[report_generator] Final report persisted to DB for session {session.session_id}")
    except Exception as db_err:
        print(f"[report_generator] ⚠ Failed to persist report to DB: {db_err}")
    
    update_session(session)

    print(
        f"[report_generator] Session complete | "
        f"accuracy={accuracy}% | theta={theta_final:.2f} | skill={skill_label.value}"
    )
    return {"session": session, "action": "done"}