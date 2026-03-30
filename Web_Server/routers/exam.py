import json
import os
from datetime import date as _date, datetime as _datetime
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database import SessionLocal
from app.models import (
    Answer,
    Candidate,
    Drive,
    DriveRegistration,
    ExamAttempt,
    ExamResult,
    ExamSection,
    Offer,
    Question,
    User,
    Vendor,
    CodingQuestion,
    TestCase,
    CodeSubmission,
    ExamLaunchCode,
    JitSectionSession,
    JitAnswerEvent,
)
from app.schemas.exam_schema import (
    CreateExamRequest,
    CreateQuestionRequest,
    CreateSectionRequest,
    JitSectionInput,
    UpdateExamRequest,
    UpdateQuestionRequest,
    UpdateSectionRequest,
)
from app.security import decode_access_token
from app.storage import supabase

router = APIRouter(prefix="/admin/exams", tags=["admin-exams"])
security = HTTPBearer()


ALLOWED_GENERATION_MODES = {"static", "jit", "morphing"}
ALLOWED_QUESTION_TYPES = {
    "MCQ",
    "MSQ",
    "Fill in the Blanks",
    "Numeric",
    "Short Answer",
    "Long Answer",
    "Coding",
}
ALLOWED_JIT_QUESTION_TYPES = {"mcq", "msq", "fib", "numerical", "short", "long", "coding", "mixed"}
ALLOWED_TAXONOMY_LEVELS = {1, 2, 3, 4, 5}
GENERAL_MORPHING_STRATEGIES = {"rephrase", "contextual", "distractor", "structural", "difficulty"}
CODING_MORPHING_STRATEGIES = {
    "code_rephrase",
    "code_contextual",
    "code_difficulty",
    "code_constraint",
    "code_tcgen",
    "code_tcscale",
}
REPORT_LINK_TTL_SECONDS = int(os.getenv("REPORT_LINK_TTL_SECONDS", "86400"))
RENDERING_SERVICE_URL = str(
    os.getenv("RENDERING_SERVICE_URL")
    or os.getenv("REPORT_RENDERING_SERVICE_URL")
    or ""
).strip().rstrip("/")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _normalize_tag_list(values: list[str] | None) -> list[str]:
    if not values:
        return []

    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        item = str(value or "").strip()
        if not item:
            continue
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(item)
    return normalized


def _parse_json_list(raw_value: Any) -> list[str]:
    if not raw_value:
        return []
    try:
        parsed = json.loads(str(raw_value))
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [str(item).strip() for item in parsed if str(item).strip()]


def _get_admin_context(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> dict:
    try:
        payload = decode_access_token(credentials.credentials)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    if payload.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    user_id = int(payload.get("sub", 0))
    vendor_id = int(payload.get("vendor_id", 0))

    user = db.query(User).filter(User.user_id == user_id, User.role == "admin").first()
    vendor = db.query(Vendor).filter(Vendor.vendor_id == vendor_id, Vendor.user_id == user_id).first()

    if not user or not vendor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin context not found",
        )

    return {"user": user, "vendor": vendor}


def _create_signed_storage_url(bucket: str, object_path: str, expires_in: int = 900) -> str:
    clean_bucket = str(bucket or "").strip()
    clean_path = str(object_path or "").strip()
    if not clean_bucket or not clean_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report file not found")

    try:
        signed = supabase.storage.from_(clean_bucket).create_signed_url(clean_path, int(expires_in))
        if isinstance(signed, dict):
            url = signed.get("signedURL") or signed.get("signedUrl") or signed.get("signed_url")
            if url:
                return str(url)
        if isinstance(signed, str) and signed.strip():
            return signed.strip()
    except Exception:
        pass

    public_url = supabase.storage.from_(clean_bucket).get_public_url(clean_path)
    if isinstance(public_url, dict):
        url = public_url.get("publicURL") or public_url.get("publicUrl") or public_url.get("public_url")
        if url:
            return str(url)
    if isinstance(public_url, str) and public_url.strip():
        return public_url.strip()

    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to generate report link")


def _validate_generation_mode(mode: str):
    if mode not in ALLOWED_GENERATION_MODES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="generation_mode must be one of: static, jit, morphing",
        )


def _validate_question_type(question_type: str):
    if question_type not in ALLOWED_QUESTION_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid question_type",
        )


def _validate_taxonomy_level(level: int):
    if level not in ALLOWED_TAXONOMY_LEVELS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="taxonomy_level must be between 1 and 5",
        )


def _validate_morphing_strategy(question_type: str, strategy: str | None) -> str | None:
    normalized = str(strategy or "").strip().lower()
    if not normalized:
        return None

    allowed = CODING_MORPHING_STRATEGIES if question_type == "Coding" else GENERAL_MORPHING_STRATEGIES
    if normalized not in allowed:
        allowed_values = ", ".join(sorted(allowed))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid morphing_strategy for {question_type}. Allowed: {allowed_values}",
        )
    return normalized


def _validate_jit_sections(sections: list[JitSectionInput] | None) -> list[JitSectionInput]:
    if not sections:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="jit_sections is required when generation_mode is jit",
        )

    normalized_sections: list[JitSectionInput] = []
    for idx, section in enumerate(sections, start=1):
        topic = section.topic.strip()
        if not topic:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"jit_sections[{idx}] topic is required",
            )
        if section.count <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"jit_sections[{idx}] count must be greater than 0",
            )
        question_type = str(section.question_type or "mcq").strip().lower()
        if question_type not in ALLOWED_JIT_QUESTION_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"jit_sections[{idx}] question_type must be one of: {', '.join(sorted(ALLOWED_JIT_QUESTION_TYPES))}",
            )
        normalized_sections.append(JitSectionInput(topic=topic, count=section.count, question_type=question_type))

    return normalized_sections


def _parse_iso_date(value: str | None, field_name: str):
    if not value:
        return None
    try:
        return _date.fromisoformat(value)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid {field_name}, expected YYYY-MM-DD")


def _parse_iso_datetime(value: str | None, field_name: str):
    if not value:
        return None
    try:
        return _datetime.fromisoformat(value)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid {field_name}, expected ISO 8601 format")


def _build_question_storage(question_text: str, question_type: str, payload: dict | None) -> tuple[str, str | None, str | None, str | None, str | None, str | None]:
    source_payload = dict(payload or {})

    options_value = source_payload.get("options")
    if not isinstance(options_value, list):
        options_value = []

    correct_value = source_payload.get("correct_answer")
    if correct_value is None and "correct_answers" in source_payload:
        correct_value = source_payload.get("correct_answers")
    if correct_value is None and "model_answer" in source_payload:
        correct_value = source_payload.get("model_answer")

    payload_data = dict(source_payload)
    payload_data["options"] = options_value
    payload_data["correct_answer"] = correct_value
    payload_data["question_test"] = question_text

    option_a = None
    option_b = None
    option_c = None
    option_d = None
    correct_option = None

    options = payload_data.get("options")
    if isinstance(options, list):
        padded = [str(opt or "").strip() for opt in options] + [None, None, None, None]
        option_a, option_b, option_c, option_d = padded[:4]

    correct_answer = payload_data.get("correct_answer")
    if isinstance(correct_answer, list):
        normalized = [str(v or "").strip().upper() for v in correct_answer if str(v or "").strip()]
        correct_option = json.dumps(normalized) if normalized else None
        payload_data["correct_answer"] = normalized
    elif correct_answer is not None:
        normalized = str(correct_answer).strip()
        if question_type in {"MCQ", "MSQ"}:
            normalized = normalized.upper()
        correct_option = normalized or None
        payload_data["correct_answer"] = normalized

    return json.dumps(payload_data), option_a, option_b, option_c, option_d, correct_option


@router.get("")
def list_exams(
    db: Session = Depends(get_db),
    admin_ctx: dict = Depends(_get_admin_context),
):
    vendor = admin_ctx["vendor"]
    exams = (
        db.query(Drive)
        .filter(Drive.vendor_id == vendor.vendor_id)
        .order_by(Drive.created_at.desc())
        .all()
    )

    rows = []
    for exam in exams:
        section_count = db.query(ExamSection).filter(ExamSection.drive_id == exam.drive_id).count()
        rows.append(
            {
                "exam_id": exam.drive_id,
                "title": exam.title,
                "exam_type": exam.exam_type,
                "duration_minutes": exam.duration_minutes,
                "max_attempts": exam.max_attempts,
                "description": exam.description,
                "generation_mode": exam.generation_mode or "static",
                "is_published": bool(exam.is_published),
                "status": exam.status,
                "section_count": section_count,
                "created_at": exam.created_at,
                "eligibility": exam.eligibility,
                "start_date": str(exam.start_date) if exam.start_date is not None else None,
                "end_date": str(exam.end_date) if exam.end_date is not None else None,
                "exam_date": exam.exam_date.isoformat() if exam.exam_date is not None else None,
                "max_marks": exam.max_marks,
                "key_topics": _parse_json_list(exam.key_topics),
                "specializations": _parse_json_list(exam.specializations),
            }
        )

    return {"exams": rows}


@router.get("/results/candidates")
def list_registered_candidates(
    db: Session = Depends(get_db),
    admin_ctx: dict = Depends(_get_admin_context),
):
    vendor = admin_ctx["vendor"]

    rows = (
        db.query(
            DriveRegistration.registration_id,
            DriveRegistration.registered_at,
            Drive.drive_id,
            Drive.title,
            Candidate.candidate_id,
            Candidate.full_name,
            User.email,
            ExamResult.result_id,
            ExamResult.score,
            ExamResult.result_status,
        )
        .join(Drive, Drive.drive_id == DriveRegistration.drive_id)
        .join(Candidate, Candidate.candidate_id == DriveRegistration.candidate_id)
        .join(User, User.user_id == Candidate.user_id)
        .outerjoin(
            ExamResult,
            (ExamResult.drive_id == DriveRegistration.drive_id)
            & (ExamResult.candidate_id == DriveRegistration.candidate_id),
        )
        .filter(Drive.vendor_id == vendor.vendor_id)
        .order_by(DriveRegistration.registered_at.desc())
        .all()
    )

    candidates: list[dict[str, Any]] = []
    for row in rows:
        status_value = str(row.result_status or "invited").strip().lower()
        if status_value in {"pass", "passed"}:
            display_status = "Completed"
        elif status_value in {"fail", "failed"}:
            display_status = "Completed"
        elif status_value == "pending_eval":
            display_status = "Pending Eval"
        else:
            display_status = "Invited"

        candidates.append(
            {
                "registration_id": row.registration_id,
                "exam_id": row.drive_id,
                "exam_title": row.title,
                "candidate_id": row.candidate_id,
                "candidate_name": row.full_name,
                "candidate_email": row.email,
                "status": display_status,
                "registered_at": row.registered_at.isoformat() if row.registered_at else None,
                "last_score": float(row.score) if row.score is not None else None,
                "result_id": row.result_id,
            }
        )

    return {"candidates": candidates}


@router.get("/results")
def list_admin_results(
    db: Session = Depends(get_db),
    admin_ctx: dict = Depends(_get_admin_context),
):
    vendor = admin_ctx["vendor"]

    rows = (
        db.query(
            ExamResult.result_id,
            ExamResult.drive_id,
            ExamResult.candidate_id,
            ExamResult.score,
            ExamResult.rank,
            ExamResult.result_status,
            ExamResult.evaluated_at,
            ExamResult.published_to_candidate,
            Drive.title,
            Drive.exam_type,
            Candidate.full_name,
            User.email,
        )
        .join(Drive, Drive.drive_id == ExamResult.drive_id)
        .join(Candidate, Candidate.candidate_id == ExamResult.candidate_id)
        .join(User, User.user_id == Candidate.user_id)
        .filter(Drive.vendor_id == vendor.vendor_id)
        .order_by(func.coalesce(ExamResult.evaluated_at, ExamResult.created_at).desc())
        .all()
    )

    results: list[dict[str, Any]] = []
    for row in rows:
        status_raw = str(row.result_status or "pending_eval").strip().lower()
        if status_raw in {"pass", "passed"}:
            status_label = "Passed"
        elif status_raw in {"fail", "failed"}:
            status_label = "Failed"
        else:
            status_label = "Pending Eval"

        results.append(
            {
                "result_id": row.result_id,
                "exam_id": row.drive_id,
                "candidate_id": row.candidate_id,
                "candidate": row.full_name,
                "candidate_email": row.email,
                "exam": row.title,
                "exam_type": row.exam_type,
                "score": float(row.score) if row.score is not None else None,
                "rank": row.rank,
                "status": status_label,
                "date_completed": row.evaluated_at.isoformat() if row.evaluated_at else None,
                "published_to_candidate": bool(row.published_to_candidate),
            }
        )

    return {"results": results}


@router.post("/results/publish")
def publish_results_to_candidates(
    payload: dict[str, Any],
    db: Session = Depends(get_db),
    admin_ctx: dict = Depends(_get_admin_context),
):
    vendor = admin_ctx["vendor"]
    result_ids = payload.get("result_ids") or []
    if not isinstance(result_ids, list) or not result_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="result_ids is required")

    valid_result_ids = [int(item) for item in result_ids if str(item).strip().isdigit()]
    if not valid_result_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No valid result_ids provided")

    rows = (
        db.query(ExamResult)
        .join(Drive, Drive.drive_id == ExamResult.drive_id)
        .filter(Drive.vendor_id == vendor.vendor_id, ExamResult.result_id.in_(valid_result_ids))
        .all()
    )

    now = _datetime.utcnow()
    for row in rows:
        row.published_to_candidate = True
        row.published_at = now

    db.commit()

    return {"message": "Results published", "published_count": len(rows)}


@router.get("/results/{result_id}/report-link")
def get_result_report_link(
    result_id: int,
    action: str = "preview",
    db: Session = Depends(get_db),
    admin_ctx: dict = Depends(_get_admin_context),
):
    vendor = admin_ctx["vendor"]

    row = (
        db.query(ExamResult)
        .join(Drive, Drive.drive_id == ExamResult.drive_id)
        .filter(ExamResult.result_id == result_id, Drive.vendor_id == vendor.vendor_id)
        .first()
    )

    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result not found")

    normalized_action = str(action or "preview").strip().lower()
    if normalized_action == "preview":
        persisted_preview_url = str(getattr(row, "report_html_url", "") or "").strip()
        if persisted_preview_url:
            return {
                "result_id": row.result_id,
                "action": "preview",
                "report_url": persisted_preview_url,
            }

        json_bucket = str(getattr(row, "report_json_bucket", "") or "").strip()
        json_path = str(getattr(row, "report_json_path", "") or "").strip()
        if not json_bucket or not json_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report JSON metadata not found for preview",
            )

        rendering_service_url = str(
            os.getenv("RENDERING_SERVICE_URL")
            or os.getenv("REPORT_RENDERING_SERVICE_URL")
            or RENDERING_SERVICE_URL
            or ""
        ).strip().rstrip("/")
        if not rendering_service_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="RENDERING_SERVICE_URL is not configured",
            )

        preview_url = (
            f"{rendering_service_url}/preview/from-storage"
            f"?bucket={quote(json_bucket, safe='')}"
            f"&path={quote(json_path, safe='')}"
        )
        return {
            "result_id": row.result_id,
            "action": "preview",
            "report_url": preview_url,
        }

    report_url = _create_signed_storage_url(
        bucket=str(getattr(row, "report_pdf_bucket", "") or ""),
        object_path=str(getattr(row, "report_pdf_path", "") or ""),
        expires_in=REPORT_LINK_TTL_SECONDS,
    )

    return {
        "result_id": row.result_id,
        "action": action,
        "report_url": report_url,
    }


@router.post("")
def create_exam(
    data: CreateExamRequest,
    db: Session = Depends(get_db),
    admin_ctx: dict = Depends(_get_admin_context),
):
    vendor = admin_ctx["vendor"]

    title = data.title.strip()
    exam_type = data.exam_type.strip()
    generation_mode = data.generation_mode.strip().lower()

    if not title:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Exam title is required")
    if not exam_type:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Exam type is required")
    if data.duration_minutes <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Duration must be greater than 0")
    if data.max_attempts <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Max attempts must be greater than 0")
    if not (data.eligibility or "").strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Eligibility is required")
    if data.max_marks is None or data.max_marks <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Max marks must be greater than 0")
    if not data.start_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Start date is required")
    if not data.end_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="End date is required")
    if not data.exam_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Exam date/time is required")

    _validate_generation_mode(generation_mode)

    jit_sections: list[JitSectionInput] = []
    if generation_mode == "jit":
        jit_sections = _validate_jit_sections(data.jit_sections)

    parsed_start_date = _parse_iso_date(data.start_date, "start_date")
    parsed_end_date = _parse_iso_date(data.end_date, "end_date")
    parsed_exam_date = _parse_iso_datetime(data.exam_date, "exam_date")

    if parsed_start_date and parsed_end_date and parsed_end_date < parsed_start_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="End date cannot be before start date")

    exam = Drive(
        vendor_id=vendor.vendor_id,
        title=title,
        exam_type=exam_type,
        duration_minutes=data.duration_minutes,
        max_attempts=data.max_attempts,
        description=(data.description or "").strip() or None,
        generation_mode=generation_mode,
        status="saved" if bool(data.is_published) else "draft",
        is_published=bool(data.is_published),
        eligibility=(data.eligibility or "").strip() or None,
        start_date=parsed_start_date,
        end_date=parsed_end_date,
        exam_date=parsed_exam_date,
        max_marks=data.max_marks,
        key_topics=json.dumps(_normalize_tag_list(data.key_topics)),
        specializations=json.dumps(_normalize_tag_list(data.specializations)),
    )

    db.add(exam)
    db.commit()
    db.refresh(exam)

    if generation_mode == "jit":
        for index, section in enumerate(jit_sections, start=1):
            db.add(
                ExamSection(
                    drive_id=exam.drive_id,
                    title=section.topic,
                    section_type="jit",
                    question_type=section.question_type,
                    order_index=index,
                    planned_question_count=section.count,
                    status="draft",
                )
            )
        db.commit()

    section_count = db.query(ExamSection).filter(ExamSection.drive_id == exam.drive_id).count()

    return {
        "message": "Exam created",
        "exam": {
            "exam_id": exam.drive_id,
            "title": exam.title,
            "exam_type": exam.exam_type,
            "duration_minutes": exam.duration_minutes,
            "max_attempts": exam.max_attempts,
            "description": exam.description,
            "generation_mode": exam.generation_mode,
            "is_published": bool(exam.is_published),
            "status": exam.status,
            "section_count": section_count,
            "created_at": exam.created_at,
            "eligibility": exam.eligibility,
            "start_date": str(exam.start_date) if exam.start_date is not None else None,
            "end_date": str(exam.end_date) if exam.end_date is not None else None,
            "exam_date": exam.exam_date.isoformat() if exam.exam_date is not None else None,
            "max_marks": exam.max_marks,
            "key_topics": _parse_json_list(exam.key_topics),
            "specializations": _parse_json_list(exam.specializations),
        },
    }


@router.patch("/{exam_id}")
def update_exam(
    exam_id: int,
    data: UpdateExamRequest,
    db: Session = Depends(get_db),
    admin_ctx: dict = Depends(_get_admin_context),
):
    vendor = admin_ctx["vendor"]

    exam = db.query(Drive).filter(Drive.drive_id == exam_id, Drive.vendor_id == vendor.vendor_id).first()
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")

    if data.title is not None:
        title = data.title.strip()
        if not title:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Exam title cannot be empty")
        setattr(exam, "title", title)

    if data.exam_type is not None:
        exam_type = data.exam_type.strip()
        if not exam_type:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Exam type cannot be empty")
        setattr(exam, "exam_type", exam_type)

    if data.duration_minutes is not None:
        if data.duration_minutes <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Duration must be greater than 0")
        setattr(exam, "duration_minutes", data.duration_minutes)

    if data.max_attempts is not None:
        if data.max_attempts <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Max attempts must be greater than 0")
        setattr(exam, "max_attempts", data.max_attempts)

    if data.description is not None:
        setattr(exam, "description", data.description.strip() or None)

    if data.eligibility is not None:
        eligibility = data.eligibility.strip()
        if not eligibility:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Eligibility cannot be empty")
        setattr(exam, "eligibility", eligibility)

    if data.max_marks is not None:
        if data.max_marks <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Max marks must be greater than 0")
        setattr(exam, "max_marks", data.max_marks)

    if data.start_date is not None:
        parsed_start_date = _parse_iso_date(data.start_date, "start_date")
        setattr(exam, "start_date", parsed_start_date)

    if data.end_date is not None:
        parsed_end_date = _parse_iso_date(data.end_date, "end_date")
        setattr(exam, "end_date", parsed_end_date)

    if data.exam_date is not None:
        parsed_exam_date = _parse_iso_datetime(data.exam_date, "exam_date")
        setattr(exam, "exam_date", parsed_exam_date)

    start_date_val = getattr(exam, "start_date", None)
    end_date_val = getattr(exam, "end_date", None)
    if start_date_val is not None and end_date_val is not None and end_date_val < start_date_val:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="End date cannot be before start date")

    if data.generation_mode is not None:
        generation_mode = data.generation_mode.strip().lower()
        _validate_generation_mode(generation_mode)
        setattr(exam, "generation_mode", generation_mode)

    if data.status is not None and data.is_published is None:
        setattr(exam, "status", data.status.strip() or str(getattr(exam, "status", "draft")))

    if data.is_published is not None:
        published = bool(data.is_published)
        setattr(exam, "is_published", published)
        setattr(exam, "status", "saved" if published else "draft")

    if data.key_topics is not None:
        setattr(exam, "key_topics", json.dumps(_normalize_tag_list(data.key_topics)))

    if data.specializations is not None:
        setattr(exam, "specializations", json.dumps(_normalize_tag_list(data.specializations)))

    db.commit()

    return {"message": "Exam updated", "exam_id": exam.drive_id}


@router.delete("/{exam_id}")
def delete_exam(
    exam_id: int,
    db: Session = Depends(get_db),
    admin_ctx: dict = Depends(_get_admin_context),
):
    vendor = admin_ctx["vendor"]

    exam = db.query(Drive).filter(Drive.drive_id == exam_id, Drive.vendor_id == vendor.vendor_id).first()
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")

    try:
        question_ids = [
            row[0]
            for row in db.query(Question.question_id).filter(Question.drive_id == exam_id).all()
        ]
        attempt_ids = [
            row[0]
            for row in db.query(ExamAttempt.attempt_id).filter(ExamAttempt.drive_id == exam_id).all()
        ]
        registration_ids = [
            row[0]
            for row in db.query(DriveRegistration.registration_id).filter(DriveRegistration.drive_id == exam_id).all()
        ]

        jit_session_ids = []
        if attempt_ids:
            jit_session_ids = [
                row[0]
                for row in db.query(JitSectionSession.jit_section_session_id)
                .filter(JitSectionSession.attempt_id.in_(attempt_ids))
                .all()
            ]

        coding_question_ids = []
        if question_ids:
            coding_question_ids = [
                row[0]
                for row in db.query(CodingQuestion.coding_question_id)
                .filter(CodingQuestion.question_id.in_(question_ids))
                .all()
            ]

        if jit_session_ids:
            db.query(JitAnswerEvent).filter(
                JitAnswerEvent.jit_section_session_id.in_(jit_session_ids)
            ).delete(synchronize_session=False)

        if attempt_ids:
            db.query(JitAnswerEvent).filter(
                JitAnswerEvent.attempt_id.in_(attempt_ids)
            ).delete(synchronize_session=False)
            db.query(JitSectionSession).filter(
                JitSectionSession.attempt_id.in_(attempt_ids)
            ).delete(synchronize_session=False)
            db.query(Answer).filter(Answer.attempt_id.in_(attempt_ids)).delete(synchronize_session=False)
            db.query(CodeSubmission).filter(
                CodeSubmission.attempt_id.in_(attempt_ids)
            ).delete(synchronize_session=False)
            db.query(ExamResult).filter(ExamResult.attempt_id.in_(attempt_ids)).delete(synchronize_session=False)

        if question_ids:
            db.query(Answer).filter(Answer.question_id.in_(question_ids)).delete(synchronize_session=False)
            db.query(CodeSubmission).filter(
                CodeSubmission.question_id.in_(question_ids)
            ).delete(synchronize_session=False)

        db.query(ExamResult).filter(ExamResult.drive_id == exam_id).delete(synchronize_session=False)
        db.query(Offer).filter(Offer.drive_id == exam_id).delete(synchronize_session=False)
        db.query(ExamLaunchCode).filter(ExamLaunchCode.drive_id == exam_id).delete(synchronize_session=False)

        if registration_ids:
            db.query(ExamLaunchCode).filter(
                ExamLaunchCode.registration_id.in_(registration_ids)
            ).delete(synchronize_session=False)

        db.query(DriveRegistration).filter(DriveRegistration.drive_id == exam_id).delete(synchronize_session=False)

        if coding_question_ids:
            db.query(TestCase).filter(
                TestCase.coding_question_id.in_(coding_question_ids)
            ).delete(synchronize_session=False)
            db.query(CodingQuestion).filter(
                CodingQuestion.coding_question_id.in_(coding_question_ids)
            ).delete(synchronize_session=False)

        if question_ids:
            db.query(Question).filter(Question.question_id.in_(question_ids)).delete(synchronize_session=False)

        db.query(ExamSection).filter(ExamSection.drive_id == exam_id).delete(synchronize_session=False)
        db.query(ExamAttempt).filter(ExamAttempt.drive_id == exam_id).delete(synchronize_session=False)

        db.delete(exam)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        db_err = str(getattr(exc, "orig", exc))
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete exam because related records still exist: {db_err}"
        )

    return {"message": "Exam deleted", "exam_id": exam_id}


@router.get("/{exam_id}/sections")
def list_sections(
    exam_id: int,
    db: Session = Depends(get_db),
    admin_ctx: dict = Depends(_get_admin_context),
):
    vendor = admin_ctx["vendor"]

    exam = db.query(Drive).filter(Drive.drive_id == exam_id, Drive.vendor_id == vendor.vendor_id).first()
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")

    sections = (
        db.query(ExamSection)
        .filter(ExamSection.drive_id == exam_id)
        .order_by(ExamSection.order_index.asc(), ExamSection.section_id.asc())
        .all()
    )

    rows = []
    for section in sections:
        question_count = db.query(Question).filter(Question.section_id == section.section_id).count()
        rows.append(
            {
                "section_id": section.section_id,
                "exam_id": section.drive_id,
                "title": section.title,
                "section_type": section.section_type,
                "question_type": section.question_type or "mcq",
                "order_index": section.order_index,
                "planned_question_count": section.planned_question_count or 0,
                "marks_weight": section.marks_weight,
                "status": section.status,
                "question_count": question_count,
                "created_at": section.created_at,
            }
        )

    return {"sections": rows}


@router.post("/{exam_id}/sections")
def create_section(
    exam_id: int,
    data: CreateSectionRequest,
    db: Session = Depends(get_db),
    admin_ctx: dict = Depends(_get_admin_context),
):
    vendor = admin_ctx["vendor"]

    exam = db.query(Drive).filter(Drive.drive_id == exam_id, Drive.vendor_id == vendor.vendor_id).first()
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")

    title = data.title.strip()
    if not title:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Section title is required")

    if data.order_index is None:
        max_order = db.query(ExamSection).filter(ExamSection.drive_id == exam_id).count()
        order_index = max_order + 1
    else:
        order_index = data.order_index

    section = ExamSection(
        drive_id=exam_id,
        title=title,
        section_type=data.section_type.strip() or "mixed",
        question_type="mcq",
        order_index=order_index,
        planned_question_count=0,
        marks_weight=data.marks_weight,
        status=data.status.strip() or "draft",
    )

    db.add(section)
    db.commit()
    db.refresh(section)

    return {
        "message": "Section created",
        "section": {
            "section_id": section.section_id,
            "exam_id": section.drive_id,
            "title": section.title,
            "section_type": section.section_type,
            "question_type": section.question_type or "mcq",
            "order_index": section.order_index,
            "planned_question_count": section.planned_question_count or 0,
            "marks_weight": section.marks_weight,
            "status": section.status,
            "question_count": 0,
            "created_at": section.created_at,
        },
    }


@router.patch("/sections/{section_id}")
def update_section(
    section_id: int,
    data: UpdateSectionRequest,
    db: Session = Depends(get_db),
    admin_ctx: dict = Depends(_get_admin_context),
):
    vendor = admin_ctx["vendor"]

    section = (
        db.query(ExamSection)
        .join(Drive, Drive.drive_id == ExamSection.drive_id)
        .filter(ExamSection.section_id == section_id, Drive.vendor_id == vendor.vendor_id)
        .first()
    )
    if not section:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")

    if data.title is not None:
        title = data.title.strip()
        if not title:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Section title cannot be empty")
        setattr(section, "title", title)

    if data.section_type is not None:
        setattr(section, "section_type", data.section_type.strip() or str(getattr(section, "section_type", "mixed")))

    if data.order_index is not None:
        setattr(section, "order_index", data.order_index)

    if data.marks_weight is not None:
        setattr(section, "marks_weight", data.marks_weight)

    if data.status is not None:
        setattr(section, "status", data.status.strip() or str(getattr(section, "status", "draft")))

    db.commit()

    return {"message": "Section updated", "section_id": section.section_id}


@router.delete("/sections/{section_id}")
def delete_section(
    section_id: int,
    db: Session = Depends(get_db),
    admin_ctx: dict = Depends(_get_admin_context),
):
    vendor = admin_ctx["vendor"]

    section = (
        db.query(ExamSection)
        .join(Drive, Drive.drive_id == ExamSection.drive_id)
        .filter(ExamSection.section_id == section_id, Drive.vendor_id == vendor.vendor_id)
        .first()
    )
    if not section:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")

    question_ids = [row[0] for row in db.query(Question.question_id).filter(Question.section_id == section.section_id).all()]
    jit_session_ids = [
        row[0]
        for row in db.query(JitSectionSession.jit_session_id)
        .filter(JitSectionSession.section_id == section.section_id)
        .all()
    ]

    try:
        if jit_session_ids:
            db.query(JitAnswerEvent).filter(JitAnswerEvent.jit_session_id.in_(jit_session_ids)).delete(
                synchronize_session=False
            )
        db.query(JitSectionSession).filter(JitSectionSession.section_id == section.section_id).delete(
            synchronize_session=False
        )

        if question_ids:
            db.query(Answer).filter(Answer.question_id.in_(question_ids)).delete(synchronize_session=False)
            db.query(CodeSubmission).filter(CodeSubmission.question_id.in_(question_ids)).delete(synchronize_session=False)

            coding_question_ids = [
                row[0]
                for row in db.query(CodingQuestion.coding_question_id)
                .filter(CodingQuestion.question_id.in_(question_ids))
                .all()
            ]
            if coding_question_ids:
                db.query(TestCase).filter(TestCase.coding_question_id.in_(coding_question_ids)).delete(
                    synchronize_session=False
                )

            db.query(CodingQuestion).filter(CodingQuestion.question_id.in_(question_ids)).delete(
                synchronize_session=False
            )
            db.query(Question).filter(Question.question_id.in_(question_ids)).delete(synchronize_session=False)

        db.delete(section)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Unable to hard delete section due to related records: {exc.orig}",
        )

    return {"message": "Section deleted", "section_id": section_id}


@router.get("/sections/{section_id}/questions")
def list_questions(
    section_id: int,
    db: Session = Depends(get_db),
    admin_ctx: dict = Depends(_get_admin_context),
):
    vendor = admin_ctx["vendor"]

    section = (
        db.query(ExamSection)
        .join(Drive, Drive.drive_id == ExamSection.drive_id)
        .filter(ExamSection.section_id == section_id, Drive.vendor_id == vendor.vendor_id)
        .first()
    )
    if not section:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")

    questions = (
        db.query(Question)
        .filter(Question.section_id == section_id)
        .order_by(Question.question_id.desc())
        .all()
    )

    rows = []
    for question in questions:
        payload = None
        raw_payload = getattr(question, "payload_json", None)
        if raw_payload:
            try:
                payload = json.loads(str(raw_payload))
            except json.JSONDecodeError:
                payload = None

        rows.append(
            {
                "question_id": question.question_id,
                "section_id": question.section_id,
                "question_text": question.question_text,
                "question_type": question.question_type or "MCQ",
                "taxonomy_level": question.taxonomy_level or 3,
                "marks": question.marks,
                "morphing_strategy": question.morphing_strategy,
                "time_complexity": question.time_complexity,
                "space_complexity": question.space_complexity,
                "payload": payload,
            }
        )

    return {"questions": rows}


@router.post("/sections/{section_id}/questions")
def create_question(
    section_id: int,
    data: CreateQuestionRequest,
    db: Session = Depends(get_db),
    admin_ctx: dict = Depends(_get_admin_context),
):
    vendor = admin_ctx["vendor"]

    section = (
        db.query(ExamSection)
        .join(Drive, Drive.drive_id == ExamSection.drive_id)
        .filter(ExamSection.section_id == section_id, Drive.vendor_id == vendor.vendor_id)
        .first()
    )
    if not section:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")

    question_text = data.question_text.strip()
    if not question_text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Question text is required")
    if data.marks <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Marks must be greater than 0")

    question_type = data.question_type.strip()
    _validate_question_type(question_type)
    _validate_taxonomy_level(data.taxonomy_level)
    morphing_strategy = _validate_morphing_strategy(question_type, data.morphing_strategy)

    payload_json, option_a, option_b, option_c, option_d, correct_option = _build_question_storage(
        question_text,
        question_type,
        data.payload,
    )

    question = Question(
        drive_id=section.drive_id,
        section_id=section.section_id,
        question_text=question_text,
        question_type=question_type,
        marks=data.marks,
        payload_json=payload_json,
        option_a=option_a,
        option_b=option_b,
        option_c=option_c,
        option_d=option_d,
        correct_option=correct_option,
        taxonomy_level=data.taxonomy_level,
        morphing_strategy=morphing_strategy,
        time_complexity=(data.time_complexity or "").strip() or None,
        space_complexity=(data.space_complexity or "").strip() or None,
    )

    db.add(question)
    db.commit()
    db.refresh(question)

    return {
        "message": "Question created",
        "question": {
            "question_id": question.question_id,
            "section_id": question.section_id,
            "question_text": question.question_text,
            "question_type": question.question_type,
            "taxonomy_level": question.taxonomy_level,
            "marks": question.marks,
            "morphing_strategy": question.morphing_strategy,
            "time_complexity": question.time_complexity,
            "space_complexity": question.space_complexity,
            "payload": data.payload,
        },
    }


@router.patch("/questions/{question_id}")
def update_question(
    question_id: int,
    data: UpdateQuestionRequest,
    db: Session = Depends(get_db),
    admin_ctx: dict = Depends(_get_admin_context),
):
    vendor = admin_ctx["vendor"]

    question = (
        db.query(Question)
        .join(ExamSection, ExamSection.section_id == Question.section_id)
        .join(Drive, Drive.drive_id == ExamSection.drive_id)
        .filter(Question.question_id == question_id, Drive.vendor_id == vendor.vendor_id)
        .first()
    )
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

    if data.question_text is not None:
        question_text = data.question_text.strip()
        if not question_text:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Question text cannot be empty")
        setattr(question, "question_text", question_text)

    if data.question_type is not None:
        question_type = data.question_type.strip()
        _validate_question_type(question_type)
        setattr(question, "question_type", question_type)

    effective_type = str(getattr(question, "question_type", "MCQ") or "MCQ")

    if data.morphing_strategy is not None:
        setattr(question, "morphing_strategy", _validate_morphing_strategy(effective_type, data.morphing_strategy))

    if data.time_complexity is not None:
        setattr(question, "time_complexity", data.time_complexity.strip() or None)

    if data.space_complexity is not None:
        setattr(question, "space_complexity", data.space_complexity.strip() or None)

    if data.marks is not None:
        if data.marks <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Marks must be greater than 0")
        setattr(question, "marks", data.marks)

    if data.taxonomy_level is not None:
        _validate_taxonomy_level(data.taxonomy_level)
        setattr(question, "taxonomy_level", data.taxonomy_level)

    if data.payload is not None:
        effective_text = str(question.question_text)
        effective_type = str(question.question_type or "MCQ")
        payload_json, option_a, option_b, option_c, option_d, correct_option = _build_question_storage(
            effective_text,
            effective_type,
            data.payload,
        )
        setattr(question, "payload_json", payload_json)
        setattr(question, "option_a", option_a)
        setattr(question, "option_b", option_b)
        setattr(question, "option_c", option_c)
        setattr(question, "option_d", option_d)
        setattr(question, "correct_option", correct_option)

    elif data.question_text is not None or data.question_type is not None:
        payload = None
        raw_payload = getattr(question, "payload_json", None)
        if raw_payload:
            try:
                payload = json.loads(str(raw_payload))
            except json.JSONDecodeError:
                payload = {}
        payload_json, option_a, option_b, option_c, option_d, correct_option = _build_question_storage(
            str(question.question_text),
            str(question.question_type or "MCQ"),
            payload,
        )
        setattr(question, "payload_json", payload_json)
        setattr(question, "option_a", option_a)
        setattr(question, "option_b", option_b)
        setattr(question, "option_c", option_c)
        setattr(question, "option_d", option_d)
        setattr(question, "correct_option", correct_option)

    db.commit()

    return {"message": "Question updated", "question_id": question.question_id}


@router.delete("/questions/{question_id}")
def delete_question(
    question_id: int,
    db: Session = Depends(get_db),
    admin_ctx: dict = Depends(_get_admin_context),
):
    vendor = admin_ctx["vendor"]

    question = (
        db.query(Question)
        .join(ExamSection, ExamSection.section_id == Question.section_id)
        .join(Drive, Drive.drive_id == ExamSection.drive_id)
        .filter(Question.question_id == question_id, Drive.vendor_id == vendor.vendor_id)
        .first()
    )
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

    db.delete(question)
    db.commit()

    return {"message": "Question deleted", "question_id": question_id}
