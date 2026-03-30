"""
LLM Summary Agent using Groq API + Llama 3.3 70B
Generates candidate analysis, section insights, and hiring recommendation.
"""

import os
import json
import httpx
from typing import Any, Optional
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root (report_agent/.env) for CLI and API usage.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


async def generate_candidate_summary(report_data: dict) -> dict:
    """
    Calls Groq API with exam data and returns structured AI summary.
    Returns keys used by the report template, including report_declaration.
    """
    if not GROQ_API_KEY:
        return _fallback_summary(report_data)

    prompt = _build_prompt(report_data)

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                GROQ_API_URL,
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": MODEL,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are an expert HR analyst and technical evaluator. "
                                "Analyze exam results and provide a structured, professional candidate assessment. "
                                "Always respond with valid JSON only — no markdown, no preamble."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 1200,
                    "response_format": {"type": "json_object"},
                },
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            summary = json.loads(content)
            summary.setdefault("report_declaration", _default_report_declaration(report_data))
            return summary

    except Exception as e:
        print(f"[LLM] Groq API error: {e}")
        return _fallback_summary(report_data)


def _build_prompt(data: dict) -> str:
    candidate = data["candidate"]
    exam = data["exam"]
    attempt = data["attempt"]
    sections = data["sections"]
    proctoring = data["proctoring"]

    # Build section performance summary
    section_lines = []
    for s in sections:
        earned = s.get("marks_earned", 0)
        total = s.get("total_marks", 0)
        pct = round((earned / total) * 100, 1) if total else 0
        section_lines.append(
            f"  - {s['title']}: {earned}/{total} ({pct}%)"
        )
    section_summary = "\n".join(section_lines) if section_lines else "  - No section data available"

    # LLM section breakdown from attempt
    llm_lines = []
    for sb in attempt.get("section_breakdown", []):
        earned = sb.get("earned", 0)
        total = sb.get("total", 0)
        pct = round((earned / total) * 100, 1) if total else 0
        llm_lines.append(f"  - {sb['section_title']}: {earned}/{total} ({pct}%)")
    llm_summary = "\n".join(llm_lines) if llm_lines else section_summary

    # Proctoring flags
    alert_types = [a["alert_type"] for a in proctoring.get("alerts", [])]
    alert_summary = ", ".join(set(alert_types)) if alert_types else "None"
    alert_count = proctoring.get("total_alerts", 0)

    # JIT topic strength
    jit_strength = attempt.get("jit_topic_strength", {})
    jit_lines = [f"  - {topic}: {score}" for topic, score in jit_strength.items()]
    jit_text = "\n".join(jit_lines) if jit_lines else "  - Not available"

    total_earned = attempt.get("total_marks_earned", 0)
    is_jit = bool(attempt.get("has_jit") or data.get("mode") == "jit")
    total_possible = attempt.get("llm_total_marks", 0) or exam.get("max_marks", 0)
    overall_pct = None if is_jit else (round((total_earned / total_possible) * 100, 1) if total_possible else None)
    jit_proficiency_pct = _derive_jit_proficiency_pct(attempt) if is_jit else None
    overall_score_line = (
        f"OVERALL SCORE: {total_earned}/{total_possible} ({overall_pct}%)"
        if overall_pct is not None
        else (
            f"OVERALL SCORE: {total_earned} (adaptive JIT marks; not directly comparable to fixed-mark percentage). "
            f"Derived proficiency estimate: {jit_proficiency_pct}%"
            if jit_proficiency_pct is not None
            else f"OVERALL SCORE: {total_earned} (adaptive JIT marks; fixed percentage unavailable)"
        )
    )

    return f"""
Analyze the following exam result and return a JSON object with exactly these keys:
- "overview": string (2-3 sentences analyzing this candidate's overall performance and exam engagement)
- "strengths": list of 3 strings (specific technical or behavioral strengths demonstrated in the exam)
- "weaknesses": list of 3 strings (specific areas of deficiency or concern from the exam data)
- "proctoring_assessment": string (1-2 sentences on exam integrity and candidate conduct)
- "recommendation": string (3-4 sentences with clear hiring decision and rationale)
- "report_declaration": string (2-3 formal sentences suitable for the final declaration page in this report)
- "verdict": string — must be exactly one of: "STRONGLY RECOMMEND" | "RECOMMEND" | "BORDERLINE" | "NOT RECOMMENDED"
- "confidence_score": number between 0 and 100 (how confident in this verdict)

CANDIDATE: {candidate['full_name']}
EXPERIENCE: {candidate['years_of_experience']} years
EXAM: {exam['title']} ({exam['exam_type']})
COMPANY: {exam['company_name']}

{overall_score_line}
RESULT: {attempt['result']}
MODE: {data['mode']}
DURATION: {exam['duration_minutes']} minutes

SECTION PERFORMANCE (identify strongest and weakest sections):
{llm_summary}

JIT TOPIC STRENGTH (if available):
{jit_text}

PROCTORING ALERTS: {alert_count}
ALERT TYPES: {alert_summary}

**INSTRUCTIONS:**
1. **Strengths**: Identify specific sections or topics where the candidate scored high (60%+). Reference actual section names/scores.
2. **Weaknesses**: Identify specific sections or topics where the candidate scored low (<60%). Reference actual section names/scores.
3. **Verdict criteria**: <40%=NOT_RECOMMENDED, 40-59%=BORDERLINE, 60-79%=RECOMMEND, 80%+=STRONGLY_RECOMMEND. Deduct one level if 2+ severe proctoring alerts exist.
4. **professional tone**: Be objective, data-driven, and hiring-focused.
5. **report_declaration** must be neutral, audit-friendly, and should not mention model names, vendors, or legal disclaimers.
6. **Response MUST be valid JSON only — no markdown, no explanation outside JSON.**
"""


def _default_report_declaration(data: dict) -> str:
    """Build a neutral fallback declaration for the final page."""
    candidate = data.get("candidate", {})
    exam = data.get("exam", {})
    attempt = data.get("attempt", {})
    proctoring = data.get("proctoring", {})

    mode = "JIT" if data.get("mode") == "jit" else "LLM-morphed"
    alert_count = proctoring.get("total_alerts", 0)

    return (
        f"This report summarizes the assessment outcome for {candidate.get('full_name', 'the candidate')} "
        f"in {exam.get('title', 'the exam')} conducted for {exam.get('company_name', 'the organization')} "
        f"(mode: {mode}, attempt ID: {attempt.get('attempt_id', 'N/A')}). "
        f"Section-level performance metrics and proctoring observations are compiled from platform records, "
        f"including {alert_count} integrity alert(s) where applicable. "
        "Final hiring decisions should be made by authorized reviewers after validating all evidence and business criteria."
    )


def _derive_jit_proficiency_pct(attempt: dict) -> Optional[float]:
    """Estimate JIT proficiency from topic mastery percentages when available."""
    jit_strength = attempt.get("jit_topic_strength") or {}
    mastery_values = []

    for section_data in jit_strength.values():
        if not isinstance(section_data, dict):
            continue
        topic_strength = section_data.get("topic_strength") or {}
        sub_topic_mastery = topic_strength.get("sub_topic_mastery") or {}
        for value in sub_topic_mastery.values():
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                continue
            if 0 <= numeric <= 100:
                mastery_values.append(numeric)

    if not mastery_values:
        return None

    return round(sum(mastery_values) / len(mastery_values), 1)


def _fallback_summary(data: dict) -> dict:
    """Rule-based fallback: analyze exam data to generate dynamic, exam-specific insights."""
    attempt = data["attempt"]
    exam = data["exam"]
    sections = data.get("sections", [])
    proctoring = data.get("proctoring", {})
    candidate = data.get("candidate", {})

    total = attempt.get("total_marks_earned", 0)
    is_jit = bool(attempt.get("has_jit") or data.get("mode") == "jit")
    max_m = attempt.get("llm_total_marks", 0) or exam.get("max_marks", 0)
    jit_proficiency_pct = _derive_jit_proficiency_pct(attempt) if is_jit else None

    if is_jit:
        pct = jit_proficiency_pct
    else:
        pct = round((total / max_m) * 100, 1) if max_m else None

    alert_count = proctoring.get("total_alerts", 0)
    alert_types = [a.get("alert_type", "Unknown") for a in proctoring.get("alerts", [])]

    # Analyze section performance
    passed_sections = []
    weak_sections = []
    for sec in sections:
        earned = sec.get("marks_earned", 0)
        total_s = sec.get("total_marks", 1)
        sec_pct = (earned / total_s * 100) if total_s else 0
        if sec_pct >= 60:
            passed_sections.append((sec.get("title", "Unknown"), sec_pct))
        else:
            weak_sections.append((sec.get("title", "Unknown"), sec_pct))

    # Determine verdict
    if pct is None:
        attempt_result = str(attempt.get("result", "")).upper()
        if attempt_result == "PASS":
            verdict = "RECOMMEND"
            confidence = 60
        elif attempt_result == "FAIL":
            verdict = "NOT RECOMMENDED"
            confidence = 70
        else:
            verdict = "BORDERLINE"
            confidence = 50
    elif pct >= 80:
        verdict = "STRONGLY RECOMMEND"
        confidence = 85
    elif pct >= 60:
        verdict = "RECOMMEND"
        confidence = 70
    elif pct >= 40:
        verdict = "BORDERLINE"
        confidence = 55
    else:
        verdict = "NOT RECOMMENDED"
        confidence = 80

    # Adjust for proctoring alerts
    if alert_count >= 3:
        if verdict in ("STRONGLY RECOMMEND", "RECOMMEND"):
            verdict = "BORDERLINE"
            confidence = max(confidence - 20, 30)
    elif alert_count >= 1 and verdict == "STRONGLY RECOMMEND":
        verdict = "RECOMMEND"
        confidence = max(confidence - 10, 60)

    # Build dynamic strengths from actual performance
    strengths = []
    if passed_sections:
        strong_sec = max(passed_sections, key=lambda x: x[1])
        strengths.append(f"Strong performance in {strong_sec[0]} ({strong_sec[1]:.0f}%)")
    if pct is not None and pct >= 70:
        strengths.append("Demonstrated solid grasp of core concepts")
    elif is_jit and (jit_proficiency_pct is not None and jit_proficiency_pct >= 60):
        strengths.append(f"Adaptive topic mastery indicates solid proficiency ({jit_proficiency_pct}%)")
    if alert_count == 0:
        strengths.append("Maintained focus and exam integrity throughout")
    if not strengths:
        strengths = ["Attempted all sections", "Persisted to exam completion"]
    strengths = strengths[:3]

    # Build dynamic weaknesses from actual performance
    weaknesses = []
    if weak_sections:
        weak_sec = min(weak_sections, key=lambda x: x[1])
        weaknesses.append(f"Below-threshold performance in {weak_sec[0]} ({weak_sec[1]:.0f}%)")
    if pct is not None and pct < 50:
        weaknesses.append("Overall score below acceptable threshold for role")
    elif is_jit and jit_proficiency_pct is None:
        weaknesses.append("Insufficient fixed-mark data to benchmark performance percentile")
    if alert_count > 0:
        alert_str = ", ".join(set(alert_types[:2]))
        weaknesses.append(f"Proctoring concerns flagged: {alert_str}")
    if not weaknesses:
        weaknesses = ["Limited standout performance", "Room for improvement in technical depth"]
    weaknesses = weaknesses[:3]

    # Build exam-specific overview
    mode_text = "JIT" if data.get("mode") == "jit" else "LLM-morphed"
    if pct is not None:
        overview = (
            f"{candidate.get('full_name', 'Candidate')} scored {pct}% on the {exam.get('title', 'exam')} "
            f"({mode_text} mode, {exam.get('duration_minutes', 0)} mins). "
            f"Performance indicates a {verdict.lower()} profile. "
        )
    else:
        overview = (
            f"{candidate.get('full_name', 'Candidate')} completed the {exam.get('title', 'exam')} "
            f"({mode_text} mode, {exam.get('duration_minutes', 0)} mins) with adaptive scoring. "
            f"Performance indicates a {verdict.lower()} profile. "
        )
    if alert_count > 0:
        overview += f"{alert_count} proctoring event(s) flagged for review."
    else:
        overview += "Exam integrity maintained."

    recommendation_text = (
        f"Candidate is {verdict.lower().replace('_', ' ')} for the {exam.get('title', 'position')}. "
        + (
            f"Score of {pct}% {'exceeds expectations' if pct >= 75 else 'meets minimum' if pct >= 50 else 'falls below'} threshold. "
            if pct is not None
            else "Adaptive performance was evaluated without fixed-mark percentage normalization. "
        )
        + ("Proctoring flags require investigation. " if alert_count > 0 else "No compliance concerns. ")
        + (
            "Recommend moving to next evaluation stage."
            if ((pct is not None and pct >= 60) or (pct is None and verdict in ("RECOMMEND", "STRONGLY RECOMMEND")))
            else "Consider alternative candidates or remedial assessment."
        )
    )

    return {
        "overview": overview,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "proctoring_assessment": (
            f"No integrity concerns detected."
            if alert_count == 0
            else f"{alert_count} proctoring alert(s): {', '.join(set(alert_types[:2]))}. Evidence captured for HR review."
        ),
        "recommendation": recommendation_text,
        "verdict": verdict,
        "confidence_score": confidence,
        "report_declaration": _default_report_declaration(data),
    }
