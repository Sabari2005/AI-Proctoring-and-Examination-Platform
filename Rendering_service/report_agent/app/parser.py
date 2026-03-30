"""
Parser & normalizer for both exam JSON formats:
  - generation_mode: "jit"
  - generation_mode: "morphing"

Produces a unified `report_data` dict used by HTML preview and llm_summary.
"""

from typing import Any
from datetime import datetime
import re


def parse_report_input(payload: dict) -> dict:
    mode = payload.get("exam_mode", {}).get("generation_mode", "unknown")
    user = payload.get("user_details", {})
    exam = payload.get("exam_details", {})
    summary = payload.get("summary", {}) or {}
    attempt = payload.get("attempt", {}).get("selected_attempt", {})

    questions_raw = payload.get("questions") or {}
    sections_raw = payload.get("sections") or []

    report = {
        "mode": mode,
        "generated_at": datetime.utcnow().isoformat(),
        "candidate": _parse_candidate(user),
        "exam": _parse_exam(exam),
        "attempt": _parse_attempt(attempt, mode=mode, exam=exam, summary=summary),
        "sections": [],
        "proctoring": {},
        "ai_summary": None,
        "questions": _parse_questions(questions_raw, sections_raw),
        "all_attempts": _parse_all_attempts(payload.get("attempt", {}).get("all_attempts", [])),
    }

    # Parse sections & Q&A
    sections_raw = payload.get("sections") or []
    report["sections"] = _parse_sections(sections_raw, mode)

    # Parse proctoring alerts + evidence images
    # Support both: payload["proctoring"] and payload["proctoring_artifacts"]
    proc_raw = payload.get("proctoring") or {}
    proc_artifacts = payload.get("proctoring_artifacts") or {}
    report["proctoring"] = _parse_proctoring(proc_raw, proc_artifacts)

    # Derived display helpers
    report["display_name"] = report["candidate"]["full_name"]
    report["display_org"] = report["exam"]["company_name"]
    report["display_country"] = report["candidate"]["country"]

    return report



# ──────────────────────────────────────────────
# Sub-parsers
# ──────────────────────────────────────────────

def _parse_candidate(u: dict) -> dict:
    photo_url = (
        u.get("photo_url")
        or u.get("profile_url")
        or u.get("profile_pic")
        or u.get("avatar_url")
        or u.get("image_url")
        or u.get("photo")
        or ""
    )
    photo_b64 = u.get("photo_b64", "")
    if not photo_b64 and isinstance(photo_url, str) and photo_url.startswith("data:image/"):
        photo_b64 = photo_url

    return {
        "user_id": u.get("user_id"),
        "candidate_id": u.get("candidate_id"),
        "full_name": u.get("full_name", "Unknown"),
        "email": u.get("email", ""),
        "mobile": u.get("mobile_no", ""),
        "country": u.get("country", ""),
        "timezone": u.get("timezone", ""),
        "photo_url": photo_url,
        "photo_b64": photo_b64,
        "years_of_experience": u.get("years_of_experience", 0),
        "is_active": u.get("is_active", False),
    }


def _parse_exam(e: dict) -> dict:
    return {
        "drive_id": e.get("drive_id"),
        "title": e.get("title", "Untitled Exam"),
        "description": e.get("description") or "",
        "eligibility": e.get("eligibility", ""),
        "exam_type": e.get("exam_type", ""),
        "start_date": e.get("start_date", ""),
        "end_date": e.get("end_date", ""),
        "exam_date": _fmt_dt(e.get("exam_date", "")),
        "duration_minutes": e.get("duration_minutes", 0),
        "max_attempts": e.get("max_attempts"),
        "max_marks": e.get("max_marks", 0),
        "company_name": e.get("company_name", ""),
        "organization_type": e.get("organization_type", ""),
        "organization_email": e.get("organization_email", ""),
    }


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_attempt(a: dict, mode: str, exam: dict, summary: dict) -> dict:
    total = a.get("computed_total_marks", 0)
    breakdown_raw = a.get("computed_breakdown", {})
    # Normalize breakdown to ensure all required keys exist
    breakdown = {
        "regular_marks": breakdown_raw.get("regular_marks", 0),
        "llm_morphed_marks": breakdown_raw.get("llm_morphed_marks", 0),
        "jit_marks": breakdown_raw.get("jit_marks", 0),
        "coding_marks": breakdown_raw.get("coding_marks", 0),
    }
    llm_total = a.get("llm_morphed_total_marks", 0)
    is_jit = str(mode or "").strip().lower() == "jit" or bool(a.get("has_jit", False))

    # Determine overall result.
    # JIT-only rule: use summary.exam_max_marks and summary.selected_attempt_computed_total_marks.
    # Non-JIT keeps existing fallback behavior.
    result = ""
    result_percentage = None
    jit_exam_max_marks = None
    if is_jit:
        computed_total = _to_float(summary.get("selected_attempt_computed_total_marks"), _to_float(total, 0.0))
        exam_max_marks = _to_float(summary.get("exam_max_marks"), _to_float(exam.get("max_marks"), 0.0))
        if exam_max_marks > 0:
            result_percentage = (computed_total / exam_max_marks) * 100.0
            result = "pass" if computed_total >= exam_max_marks else "fail"
            jit_exam_max_marks = exam_max_marks
        else:
            # If max marks is unavailable, trust explicit final decision from summary if present.
            result = str(summary.get("final_decision") or "").strip().lower()
    else:
        result = str(a.get("llm_morphed_result") or "").strip().lower() or _compute_result(total, llm_total or 100)

    if not result:
        result = "pending"

    # Section-level LLM breakdown
    section_breakdown = []
    for s in a.get("llm_section_breakdown", []):
        section_breakdown.append({
            "section_id": s.get("section_id"),
            "section_title": s.get("section_title"),
            "earned": s.get("llm_morphed_marks", 0),
            "total": s.get("llm_morphed_total_marks", 0),
        })

    return {
        "attempt_id": a.get("attempt_id"),
        "start_time": _fmt_dt(a.get("start_time", "")),
        "end_time": _fmt_dt(a.get("end_time", "")) if a.get("end_time") else "Not submitted",
        "status": a.get("status", "unknown"),
        "total_marks_earned": total,
        "breakdown": breakdown,
        "llm_total_marks": llm_total,
        "result": result.upper() if result else "PENDING",
        "section_breakdown": section_breakdown,
        "llm_section_breakdown": a.get("llm_section_breakdown", []),
        "llm_raw_question_count": a.get("llm_raw_question_count"),
        "llm_effective_question_count": a.get("llm_effective_question_count"),
        "jit_topic_strength": a.get("jit_topic_strength", {}),
        "has_jit": is_jit,
        "has_coding": a.get("has_coding", False),
        "jit_exam_max_marks": jit_exam_max_marks,
        "result_percentage": result_percentage,
    }


def _parse_sections(sections: list, mode: str) -> list:
    parsed = []
    for sec in sections:
        questions = []
        for q in sec.get("questions", []):
            questions.append(_parse_question(q, mode))

        parsed.append({
            "section_id": sec.get("section_id"),
            "title": sec.get("title") or sec.get("section_title", "Section"),
            "description": sec.get("description", ""),
            "marks_earned": sec.get("marks_earned", 0),
            "total_marks": sec.get("total_marks", 0),
            "questions": questions,
        })
    return parsed


def _parse_question(q: dict, mode: str) -> dict:
    qtype = q.get("question_type", "mcq")
    answer_obj = q.get("answer") or {}

    # Handle various answer shapes
    candidate_answer = (
        answer_obj.get("selected_option")
        or answer_obj.get("answer_text")
        or answer_obj.get("code")
        or answer_obj.get("essay_text")
        or ""
    )

    correct_answer = (
        q.get("correct_answer")
        or q.get("correct_option")
        or ""
    )

    # LLM evaluation for morphed questions
    llm_eval = q.get("llm_evaluation") or {}

    marks_earned = (
        q.get("marks_awarded")
        or q.get("marks_earned")
        or llm_eval.get("marks_awarded")
        or 0
    )
    marks_total = q.get("marks") or q.get("total_marks") or 1
    passed = bool(marks_earned and float(marks_earned) > 0)

    return {
        "question_id": q.get("question_id") or q.get("id"),
        "question_type": qtype,
        "question_text": q.get("question_text") or q.get("question") or "",
        "options": q.get("options", []),
        "candidate_answer": str(candidate_answer) if candidate_answer else "Not answered",
        "correct_answer": str(correct_answer) if correct_answer else "",
        "marks_earned": marks_earned,
        "marks_total": marks_total,
        "passed": passed,
        "is_morphed": q.get("is_morphed", False),
        "llm_feedback": llm_eval.get("feedback", ""),
        "llm_score_explanation": llm_eval.get("explanation", ""),
    }


def _parse_proctoring(proc: dict, proc_artifacts: dict = None) -> dict:
    """
    Parse proctoring alerts and group evidence images by alert (warning_folder).
    Each alert gets up to 20 images displayed as a grid on its own PDF page.
    """
    # Handle jit.json format: proctoring_artifacts.evidence_frames.items
    if proc_artifacts:
        ef = proc_artifacts.get("evidence_frames", {})
        extra_images = ef.get("items", [])
        if extra_images:
            proc.setdefault("evidence_images", [])
            proc["evidence_images"].extend(extra_images)

    alerts_raw = proc.get("alerts", [])
    images_raw = proc.get("evidence_images", [])

    # Group images by warning_folder
    image_map: dict[str, list] = {}
    for img in images_raw:
        folder = img.get("warning_folder", "unknown")
        if folder not in image_map:
            image_map[folder] = []
        image_map[folder].append({
            "url": img.get("evidence_frame", ""),
            "file_name": img.get("file_name", ""),
            "time": img.get("time", ""),
            "bucket": img.get("bucket", "evidence-frame"),
            "supabase_path": img.get("supabase_path", ""),
        })

    # Build alert list enriched with images
    parsed_alerts = []
    for alert in alerts_raw:
        folder = alert.get("warning_folder") or alert.get("folder_name", "")
        alert_images = image_map.get(folder, [])

        parsed_alerts.append({
            "alert_id": alert.get("id") or alert.get("alert_id"),
            "alert_type": alert.get("alert_type") or alert.get("type", "Unknown"),
            "severity": alert.get("severity", "medium"),
            "description": alert.get("description", ""),
            "timestamp": _fmt_dt(alert.get("timestamp") or alert.get("time", "")),
            "section_id": alert.get("sectionid") or alert.get("section_id"),
            "warning_folder": folder,
            "images": alert_images,
        })

    # Also handle case where images exist without explicit alert objects
    # (as seen in jit.json where images are nested inside proctoring directly)
    existing_folders = {a["warning_folder"] for a in parsed_alerts}
    for folder, imgs in image_map.items():
        if folder not in existing_folders:
            # Infer alert type from folder name
            alert_type = _infer_alert_type(folder)
            parsed_alerts.append({
                "alert_id": None,
                "alert_type": alert_type,
                "severity": _infer_severity(folder),
                "description": _humanize_folder(folder),
                "timestamp": imgs[0]["time"] if imgs else "",
                "section_id": None,
                "warning_folder": folder,
                "images": imgs,
            })

    return {
        "total_alerts": len(parsed_alerts),
        "alerts": parsed_alerts,
        "summary": proc.get("summary", {}),
    }


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _fmt_dt(dt_str: str) -> str:
    if not dt_str:
        return ""
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.strftime("%d %b %Y, %I:%M %p UTC")
    except Exception:
        return dt_str


def _compute_result(earned: float, total: float) -> str:
    if total == 0:
        return "pending"
    pct = (earned / total) * 100
    return "pass" if pct >= 40 else "fail"


def _infer_alert_type(folder: str) -> str:
    folder_lower = folder.lower()
    if "liveness" in folder_lower:
        return "Liveness Check Failed"
    if "face" in folder_lower and "multiple" in folder_lower:
        return "Multiple Faces Detected"
    if "no_face" in folder_lower or "face_absent" in folder_lower:
        return "Face Not Detected"
    if "tab" in folder_lower or "switch" in folder_lower:
        return "Tab Switch Detected"
    if "phone" in folder_lower:
        return "Phone Detected"
    if "person" in folder_lower:
        return "Unknown Person Detected"
    if "noise" in folder_lower or "audio" in folder_lower:
        return "Suspicious Audio"
    return "Proctoring Alert"


def _infer_severity(folder: str) -> str:
    folder_lower = folder.lower()
    if any(k in folder_lower for k in ["multiple", "phone", "person", "switch"]):
        return "high"
    if any(k in folder_lower for k in ["liveness", "face"]):
        return "medium"
    return "low"


def _humanize_folder(folder: str) -> str:
    """Convert folder name like '20260326_101643_Liveness_Only_1_blink_s_in_15s_window_require_2_possible_unb' to readable text."""
    parts = folder.split("_")
    # Remove timestamp prefix (first 2 parts if they look like date/time)
    if len(parts) > 2 and parts[0].isdigit() and parts[1].isdigit():
        parts = parts[2:]
    return " ".join(parts).replace("  ", " ").strip()


def _parse_questions(questions_raw: dict, sections_raw: list = None) -> dict:
    """Extract structured question lists from the questions payload."""
    questions_raw = questions_raw or {}

    # Build section_id -> title lookup from top-level sections
    section_title_map = {}
    for s in (sections_raw or []):
        sid = s.get("section_id")
        title = s.get("title") or s.get("section_title", "")
        if sid:
            section_title_map[sid] = title

    jit_questions = []
    for q in questions_raw.get("jit_questions", []):
        payload = q.get("question_payload") or {}
        eval_data = q.get("evaluation") or {}
        adaptive = q.get("adaptive_decision") or {}
        score = q.get("score", 0)
        if score is None:
            score = 0
        jit_questions.append({
            "question_id": q.get("question_id", ""),
            "question_number": q.get("question_number", 0),
            "section_id": q.get("section_id"),
            "section_title": q.get("section_title", ""),
            "question_text": payload.get("question_text", q.get("question_text", "")),
            "question_type": payload.get("qtype", q.get("question_type", "mcq")),
            "difficulty": payload.get("difficulty", 1),
            "bloom_level": payload.get("bloom_level", ""),
            "sub_topic": payload.get("sub_topic", ""),
            "options": payload.get("options", []),
            "correct_answers": payload.get("correct_answers", []),
            "candidate_answer": q.get("candidate_answer", ""),
            "time_taken_seconds": q.get("time_taken_seconds", 0),
            "is_correct": q.get("is_correct", False),
            "score": score,
            "feedback": eval_data.get("feedback", ""),
            "new_theta": adaptive.get("new_theta"),
            "theta_delta": adaptive.get("theta_delta"),
            "question_payload": payload,
        })

    return {
        "jit_questions": jit_questions,
        "regular_questions": questions_raw.get("regular_questions", []),
        "llm_morphed_questions": _parse_llm_morphed_qs(
            questions_raw.get("llm_morphed_questions", []),
            section_title_map
        ),
        "coding_questions": questions_raw.get("coding_questions", []),
    }


def _parse_llm_morphed_qs(raw: list, section_title_map: dict = None) -> list:
    """Parse LLM morphed question entries from the questions.llm_morphed_questions list.

    The actual JSON structure uses morphed_payload for question content:
      - morphed_payload.question  → question text
      - morphed_payload.correct_answer / correct_answers → answer(s)
      - morphed_payload.question_type → type (mcq, fill_blank, etc.)
      - morph_type → morphing strategy (difficulty, structural, etc.)
    """
    parsed = []
    section_title_map = section_title_map or {}

    for idx, q in enumerate(raw, start=1):
        morphed = q.get("morphed_payload") or {}

        # Question text: prefer morphed version, fall back to source
        question_text = (
            morphed.get("question")
            or q.get("morphed_question_text")
            or q.get("source_question_text")
            or ""
        )

        # Question type
        question_type = (
            morphed.get("question_type")
            or q.get("source_question_type")
            or "MCQ"
        )

        # Correct answer(s): morphed_payload may have correct_answers (list) or correct_answer
        correct_list = morphed.get("correct_answers") or []
        correct_single = morphed.get("correct_answer") or q.get("source_correct_answer") or ""
        if correct_list:
            correct_answers = [str(a) for a in correct_list]
        elif correct_single:
            correct_answers = [str(correct_single)]
        else:
            correct_answers = []

        # Options: prefer morphed options
        options = (
            q.get("morphed_options")
            or morphed.get("options")
            or []
        )

        # Score
        score_raw = q.get("score")
        score = float(score_raw) if score_raw is not None else 0.0

        # Candidate answer
        candidate_answer = q.get("candidate_answer") or q.get("candidate_answer_raw") or ""

        # Correctness
        is_correct = score > 0

        # Morphing strategy
        morphing_strategy = (
            q.get("morph_type")
            or morphed.get("morph_type")
            or q.get("morphing_strategy")
            or ""
        )

        # Section title lookup
        section_id = q.get("section_id")
        section_title = section_title_map.get(section_id, f"Section {section_id}")

        # Feedback from morphed_payload explanation
        feedback = morphed.get("explanation") or q.get("feedback") or ""

        parsed.append({
            "question_number": idx,
            "question_id": q.get("variant_id") or q.get("question_id"),
            "section_id": section_id,
            "section_title": section_title,
            "question_text": question_text,
            "question_type": question_type,
            "options": options,
            "correct_answers": correct_answers,
            "candidate_answer": candidate_answer,
            "is_correct": is_correct,
            "score": score,
            "max_score": q.get("max_score", 1),
            "feedback": feedback,
            "morphing_strategy": morphing_strategy,
            "taxonomy_level": q.get("taxonomy_level"),
            "semantic_score": q.get("semantic_score"),
            "difficulty_actual": q.get("difficulty_actual"),
        })
    return parsed


def _parse_all_attempts(attempts_raw: list) -> list:
    """Parse all_attempts list for the attempt history comparison table.
    Returns raw ISO date strings so the template can format them with [:16].replace('T',' ').
    """
    result = []
    for a in attempts_raw:
        breakdown = a.get("computed_breakdown", {})
        result.append({
            "attempt_id": a.get("attempt_id"),
            "start_time": a.get("start_time", ""),
            "end_time": a.get("end_time", ""),         # None → "" → template shows "—"
            "status": a.get("status", "unknown"),
            "total_marks": a.get("computed_total_marks", 0),
            "jit_marks": breakdown.get("jit_marks", 0),
            "llm_marks": breakdown.get("llm_morphed_marks", 0),
            "llm_result": a.get("llm_morphed_result", ""),
            "has_jit": a.get("has_jit", False),
            "skill_level": _extract_skill_level(a.get("jit_topic_strength", {})),
        })
    return result


def _extract_skill_level(jit_topic_strength: dict) -> str:
    """Get the dominant skill level from jit_topic_strength."""
    for sec_id, data in jit_topic_strength.items():
        if isinstance(data, dict) and "topic_strength" in data:
            return data["topic_strength"].get("skill_level", "N/A")
    return "N/A"
