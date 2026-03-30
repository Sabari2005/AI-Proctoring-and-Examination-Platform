import json
import os
import secrets
from datetime import datetime, timedelta
from urllib import error as urllib_error
from urllib import request as urllib_request

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from fastapi.responses import Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import (
    User,
    Candidate,
    CandidateIdentity,
    CandidateDocument,
    CandidateLink,
    Education,
    Skill,
    ExamAttempt,
    Question,
    Answer,
    Drive,
    DriveRegistration,
    ExamLaunchCode,
    ExamSection,
    ExamResult,
    Offer,
    Vendor,
)

from app.schemas.candidate_schema import (
    AccountUpdate,
    ProfileUpdate,
    LinksUpdate,
    OnboardingStepUpdate,
    DashboardProfileUpdate,
    SubmitAttemptAnswersRequest,
)

from app.services.upload_service import upload_file
from app.security import decode_access_token
from app.storage import supabase

router = APIRouter(prefix="/candidate", tags=["candidate"])
security = HTTPBearer()

MORPHING_SERVICE_URL = os.getenv("MORPHING_SERVICE_URL", "http://127.0.0.1:8001").strip()
MORPHING_SERVICE_TOKEN = os.getenv("MORPHING_SERVICE_TOKEN", "").strip()
MORPHING_SERVICE_TIMEOUT_SECONDS = float(os.getenv("MORPHING_SERVICE_TIMEOUT_SECONDS", "20"))
MORPHING_SERVICE_ENABLED = os.getenv("MORPHING_SERVICE_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
ALLOWED_MORPHING_STRATEGIES = {"rephrase", "contextual", "distractor", "structural", "difficulty"}
EXAM_LAUNCH_CODE_TTL_MINUTES = int(os.getenv("EXAM_LAUNCH_CODE_TTL_MINUTES", "180"))
EXAM_LAUNCH_CODE_LENGTH = int(os.getenv("EXAM_LAUNCH_CODE_LENGTH", "12"))
REPORT_LINK_TTL_SECONDS = int(os.getenv("REPORT_LINK_TTL_SECONDS", "86400"))

_DUMMY_OFFER_PDF = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n4 0 obj<</Length 63>>stream\nBT /F1 28 Tf 150 420 Td (you are selected) Tj ET\nendstream\nendobj\n5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\nxref\n0 6\n0000000000 65535 f \n0000000010 00000 n \n0000000053 00000 n \n0000000110 00000 n \n0000000236 00000 n \n0000000349 00000 n \ntrailer<</Size 6/Root 1 0 R>>\nstartxref\n419\n%%EOF\n"


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _normalized_scalar(value):
    if value is None:
        return ""
    return str(value).strip()


def _to_storage_text(value):
    if isinstance(value, (dict, list)):
        return json.dumps(value)
    return _normalized_scalar(value)


def _answers_equal(expected, received, question_type: str) -> bool:
    if isinstance(expected, list):
        expected_set = {str(v).strip().lower() for v in expected if str(v).strip()}
        if isinstance(received, list):
            received_set = {str(v).strip().lower() for v in received if str(v).strip()}
        else:
            received_set = {v.strip().lower() for v in str(received or "").split(",") if v.strip()}
        return expected_set == received_set

    if question_type == "Numeric":
        try:
            return float(expected) == float(received)
        except (TypeError, ValueError):
            return False

    return _normalized_scalar(expected).lower() == _normalized_scalar(received).lower()


def _get_candidate_from_token(
    credentials: HTTPAuthorizationCredentials,
    db: Session,
) -> Candidate:
    try:
        payload = decode_access_token(credentials.credentials)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    if payload.get("role") != "candidate":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Candidate access required"
        )

    user_id = int(payload.get("sub", 0))
    candidate_id = int(payload.get("candidate_id", 0))

    candidate = db.query(Candidate).filter(
        Candidate.candidate_id == candidate_id,
        Candidate.user_id == user_id,
    ).first()

    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate profile not found"
        )

    return candidate


def _create_signed_storage_url(bucket: str, object_path: str, expires_in: int = 900) -> str | None:
    clean_bucket = str(bucket or "").strip()
    clean_path = str(object_path or "").strip()
    if not clean_bucket or not clean_path:
        return None

    try:
        signed = supabase.storage.from_(clean_bucket).create_signed_url(clean_path, int(expires_in))
        if isinstance(signed, dict):
            url = signed.get("signedURL") or signed.get("signedUrl") or signed.get("signed_url")
            if url:
                return str(url)
        if isinstance(signed, str) and signed.strip():
            return signed.strip()
    except Exception:
        return None

    return None


def _parse_json_list(raw_value):
    if not raw_value:
        return []
    try:
        parsed = json.loads(str(raw_value))
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [str(item).strip() for item in parsed if str(item).strip()]


def _parse_question_payload(question: Question) -> dict:
    raw_payload = getattr(question, "payload_json", None)
    if not raw_payload:
        return {}
    try:
        parsed = json.loads(str(raw_payload))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _collect_question_options(question: Question, payload: dict) -> list[str]:
    options = payload.get("options")
    if isinstance(options, list):
        normalized = [str(v).strip() for v in options if str(v).strip()]
        if normalized:
            return normalized[:6]

    fallback = [
        getattr(question, "option_a", None),
        getattr(question, "option_b", None),
        getattr(question, "option_c", None),
        getattr(question, "option_d", None),
    ]
    return [str(v).strip() for v in fallback if str(v or "").strip()]


def _normalize_morph_question_type(question_type: str) -> str:
    normalized = str(question_type or "").strip().lower()
    mapping = {
        "mcq": "mcq",
        "msq": "mcq",
        "fill in the blanks": "fill_blank",
        "Numeric": "numeric",
        "fill_blank": "fill_blank",
        "true/false": "true_false",
        "true_false": "true_false",
        "short answer": "short_answer",
        "short_answer": "short_answer",
    }
    return mapping.get(normalized, "mcq")


def _normalize_difficulty(level: int | None) -> int:
    try:
        value = int(level or 3)
    except (TypeError, ValueError):
        value = 3
    return max(1, min(5, value))


def _resolve_correct_answer(raw_correct_answer, options: list[str]) -> str:
    if raw_correct_answer is None:
        return ""

    value = str(raw_correct_answer).strip()
    if not value:
        return ""

    # Handle letter-based correct answers like A/B/C/D.
    letter_to_index = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4, "F": 5}
    upper = value.upper()
    if upper in letter_to_index:
        idx = letter_to_index[upper]
        if idx < len(options):
            return options[idx]

    # Canonicalize to the exact option text with case-insensitive match.
    for option in options:
        if str(option).strip().lower() == value.lower():
            return option

    return value


# def _build_registration_morph_payload(
#     candidate_id: int,
#     exam_id: int,
#     registration_id: int,
#     db: Session,
# ) -> dict:
#     sections = (
#         db.query(ExamSection)
#         .filter(ExamSection.drive_id == exam_id)
#         .order_by(ExamSection.order_index.asc(), ExamSection.section_id.asc())
#         .all()
#     )

#     section_payloads = []
#     for section in sections:
#         questions = (
#             db.query(Question)
#             .filter(Question.drive_id == exam_id, Question.section_id == section.section_id)
#             .order_by(Question.question_id.asc())
#             .all()
#         )

#         question_payloads = []
#         for question in questions:
#             parsed_payload = _parse_question_payload(question)
#             options = _collect_question_options(question, parsed_payload)

#             correct_answer = parsed_payload.get("correct_answer")
#             if isinstance(correct_answer, list):
#                 if len(correct_answer) != 1:
#                     continue
#                 correct_answer = correct_answer[0]
#             if correct_answer is None:
#                 correct_answer = getattr(question, "correct_option", None)

#             normalized_correct = _resolve_correct_answer(correct_answer, options)
#             if not options or not normalized_correct or normalized_correct not in options:
#                 continue

#             strategy = str(getattr(question, "morphing_strategy", "") or "").strip().lower()
#             if strategy not in ALLOWED_MORPHING_STRATEGIES:
#                 strategy = "rephrase"

#             question_payloads.append(
#                 {
#                     "source_question_id": question.question_id,
#                     "question": str(getattr(question, "question_text", "") or "").strip(),
#                     "options": options,
#                     "correct_answer": normalized_correct,
#                     "question_type": _normalize_morph_question_type(getattr(question, "question_type", "MCQ")),
#                     "difficulty": _normalize_difficulty(getattr(question, "taxonomy_level", 3)),
#                     "morph_config": {
#                         "strategies": [strategy],
#                         "variant_count": 1,
#                         "preserve_answer": True,
#                         "preserve_format": True,
#                     },
#                 }
#             )

#         section_payloads.append(
#             {
#                 "section_id": section.section_id,
#                 "section_title": str(section.title or "Section"),
#                 "questions": question_payloads,
#             }
#         )
#     print(section_payloads)
#     return {
#         "candidate_id": candidate_id,
#         "exam_id": exam_id,
#         "registration_id": registration_id,
#         "sections": section_payloads,
#     }


def _build_registration_morph_payload(candidate_id, exam_id: int) -> dict:
    return {
        "candidate_id": candidate_id,
        "exam_id": exam_id,
    }


def _dispatch_morphing_registration(payload: dict) -> tuple[bool, str | None, str]:
    if not MORPHING_SERVICE_ENABLED:
        return False, None, "disabled"

    if not MORPHING_SERVICE_URL:
        return False, None, "not_configured"

    endpoint = f"{MORPHING_SERVICE_URL.rstrip('/')}/internal/v1/registrations/process"
    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if MORPHING_SERVICE_TOKEN:
        headers["x-internal-token"] = MORPHING_SERVICE_TOKEN

    request = urllib_request.Request(
        url=endpoint,
        data=body,
        headers=headers,
        method="POST",
    )
    
    try:
        with urllib_request.urlopen(request, timeout=MORPHING_SERVICE_TIMEOUT_SECONDS) as response:
            raw = response.read().decode("utf-8") if response else "{}"
            parsed = json.loads(raw or "{}")
            return True, parsed.get("job_id") or parsed.get("request_id"), str(parsed.get("status", "queued"))
    except (urllib_error.HTTPError, urllib_error.URLError, TimeoutError, json.JSONDecodeError):
        return False, None, "dispatch_failed"


def _generate_launch_code() -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(max(8, EXAM_LAUNCH_CODE_LENGTH)))


def _issue_exam_launch_code(
    db: Session,
    registration: DriveRegistration,
    candidate_id: int,
    exam_id: int,
) -> ExamLaunchCode:
    now = datetime.utcnow()

    # Invalidate older active codes for this registration before issuing a new one.
    (
        db.query(ExamLaunchCode)
        .filter(
            ExamLaunchCode.registration_id == registration.registration_id,
            ExamLaunchCode.used_at.is_(None),
            ExamLaunchCode.expires_at > now,
        )
        .update({ExamLaunchCode.used_at: now}, synchronize_session=False)
    )

    record = None
    for _ in range(5):
        code = _generate_launch_code()
        exists = db.query(ExamLaunchCode).filter(ExamLaunchCode.launch_code == code).first()
        if exists:
            continue

        record = ExamLaunchCode(
            registration_id=registration.registration_id,
            drive_id=exam_id,
            candidate_id=candidate_id,
            launch_code=code,
            expires_at=now + timedelta(minutes=max(15, EXAM_LAUNCH_CODE_TTL_MINUTES)),
        )
        db.add(record)
        db.flush()
        break

    if not record:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to generate exam launch code",
        )

    return record


def _get_active_launch_code(
    db: Session,
    candidate_id: int,
    exam_id: int,
) -> ExamLaunchCode | None:
    now = datetime.utcnow()
    return (
        db.query(ExamLaunchCode)
        .filter(
            ExamLaunchCode.candidate_id == candidate_id,
            ExamLaunchCode.drive_id == exam_id,
            ExamLaunchCode.used_at.is_(None),
            ExamLaunchCode.expires_at > now,
        )
        .order_by(ExamLaunchCode.created_at.desc(), ExamLaunchCode.launch_id.desc())
        .first()
    )


# -----------------------------
# ACCOUNT STEP
# -----------------------------

@router.post("/account")
def update_account(data: AccountUpdate, db: Session = Depends(get_db)):

    candidate = db.query(Candidate).filter(
        Candidate.candidate_id == data.candidate_id
    ).first()

    if not candidate:
        return {"error": "Candidate not found"}

    candidate.mobile_no = data.mobile_no
    candidate.country = data.country
    candidate.timezone = data.timezone
    candidate.onboarding_step = max(candidate.onboarding_step or 0, 1)

    db.commit()

    return {"message": "Account updated"}

@router.post("/identity")
async def upload_identity(
    candidate_id: int = Form(...),
    id_type: str = Form(...),
    id_number: str = Form(...),
    photo: UploadFile = File(...),
    aadhaar: UploadFile = File(...),
    db: Session = Depends(get_db)
):

    candidate = db.query(Candidate).filter(
        Candidate.candidate_id == candidate_id
    ).first()

    if not candidate:
        return {"error": "Candidate not found"}

    photo_url = upload_file(
        "photos",
        await photo.read(),
        photo.filename,
        candidate.user_id
    )

    aadhaar_url = upload_file(
        "aadhaar",
        await aadhaar.read(),
        aadhaar.filename,
        candidate.user_id
    )

    candidate.photo_url = photo_url
    candidate.onboarding_step = max(candidate.onboarding_step or 0, 2)

    identity = CandidateIdentity(
        candidate_id=candidate_id,
        id_type=id_type,
        id_number=id_number,
        id_document_url=aadhaar_url
    )

    db.add(identity)
    db.commit()

    return {"message": "Identity uploaded"}

@router.post("/profile")
def add_profile(data: ProfileUpdate, db: Session = Depends(get_db)):

    candidate = db.query(Candidate).filter(
        Candidate.candidate_id == data.candidate_id
    ).first()

    if not candidate:
        return {"error": "Candidate not found"}

    edu = Education(
        candidate_id=data.candidate_id,
        education_level=data.education_level,
        university=data.university,
        specialization=data.specialization,
        graduation_year=data.graduation_year
    )

    db.add(edu)

    candidate.years_of_experience = data.years_of_experience
    candidate.onboarding_step = max(candidate.onboarding_step or 0, 3)

    for skill in data.skills:
        db.add(Skill(
            candidate_id=data.candidate_id,
            skill_name=skill
        ))

    db.commit()

    return {"message": "Profile saved"}

@router.post("/links")
async def add_links(
    candidate_id: int = Form(...),
    linkedin: str = Form(...),
    github: str = Form(...),
    website: str = Form(None),
    resume: UploadFile = File(...),
    db: Session = Depends(get_db)
):

    candidate = db.query(Candidate).filter(
        Candidate.candidate_id == candidate_id
    ).first()

    if not candidate:
        return {"error": "Candidate not found"}

    resume_url = upload_file(
        "resumes",
        await resume.read(),
        resume.filename,
        candidate.user_id
    )

    doc = CandidateDocument(
        candidate_id=candidate_id,
        document_type="resume",
        file_url=resume_url
    )

    link = CandidateLink(
        candidate_id=candidate_id,
        linkedin="https://linkedin.com/in/"+linkedin,
        github="https://github.com/"+github,
        personal_website=website
    )

    db.add(doc)
    db.add(link)

    candidate.onboarding_step = max(candidate.onboarding_step or 0, 4)

    db.commit()

    return {"message": "Onboarding completed"}


@router.post("/update-step")
def update_onboarding_step(data: OnboardingStepUpdate, db: Session = Depends(get_db)):

    candidate = db.query(Candidate).filter(
        Candidate.candidate_id == data.candidate_id
    ).first()

    if not candidate:
        return {"error": "Candidate not found"}

    candidate.onboarding_step = data.step
    db.commit()

    return {"message": "Onboarding step updated", "onboarding_step": candidate.onboarding_step}

@router.get("/status/{candidate_id}")
def onboarding_status(candidate_id: int, db: Session = Depends(get_db)):

    candidate = db.query(Candidate).filter(
        Candidate.candidate_id == candidate_id
    ).first()

    return {
        "onboarding_step": candidate.onboarding_step
    }

@router.get("/profile/{candidate_id}")
def get_candidate_profile(candidate_id: int, db: Session = Depends(get_db)):

    candidate = db.query(Candidate).filter(
        Candidate.candidate_id == candidate_id
    ).first()

    if not candidate:
        return {"error": "Candidate not found"}

    user = db.query(User).filter(
        User.user_id == candidate.user_id
    ).first()

    return {
        "candidate_id": candidate.candidate_id,
        "full_name": candidate.full_name,
        "email": user.email if user else None,
        "mobile_no": candidate.mobile_no,
        "country": candidate.country,
        "timezone": candidate.timezone,
        "photo_url": candidate.photo_url,
        "years_of_experience": candidate.years_of_experience,
        "onboarding_step": candidate.onboarding_step
    }


@router.put("/profile")
def update_candidate_profile(data: DashboardProfileUpdate, db: Session = Depends(get_db)):

    candidate = db.query(Candidate).filter(
        Candidate.candidate_id == data.candidate_id
    ).first()

    if not candidate:
        return {"error": "Candidate not found"}

    user = db.query(User).filter(
        User.user_id == candidate.user_id
    ).first()

    if not user:
        return {"error": "User not found"}

    existing_user = db.query(User).filter(User.email == data.email).first()
    if existing_user and existing_user.user_id != user.user_id:
        return {"error": "Email already in use"}

    candidate.full_name = data.full_name.strip()
    candidate.mobile_no = data.mobile_no.strip()
    user.email = data.email.strip().lower()

    db.commit()

    return {
        "message": "Profile updated",
        "candidate_id": candidate.candidate_id,
        "full_name": candidate.full_name,
        "email": user.email,
        "mobile_no": candidate.mobile_no
    }


@router.post("/profile-photo")
async def update_profile_photo(
    candidate_id: int = Form(...),
    photo: UploadFile = File(...),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):

    try:
        payload = decode_access_token(credentials.credentials)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    token_candidate_id = int(payload.get("candidate_id", 0))
    if token_candidate_id != candidate_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to update another user's avatar"
        )

    candidate = db.query(Candidate).filter(
        Candidate.candidate_id == candidate_id
    ).first()

    if not candidate:
        return {"error": "Candidate not found"}

    photo_url = upload_file(
        "photos",
        await photo.read(),
        photo.filename,
        candidate.user_id
    )

    candidate.photo_url = photo_url
    db.commit()

    return {
        "message": "Profile photo updated",
        "candidate_id": candidate.candidate_id,
        "photo_url": candidate.photo_url
    }


@router.post("/exam-attempts/{attempt_id}/answers")
def save_attempt_answers(
    attempt_id: int,
    data: SubmitAttemptAnswersRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    try:
        payload = decode_access_token(credentials.credentials)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    if payload.get("role") != "candidate":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Candidate access required"
        )

    candidate_id = int(payload.get("candidate_id", 0))
    attempt = db.query(ExamAttempt).filter(
        ExamAttempt.attempt_id == attempt_id,
        ExamAttempt.candidate_id == candidate_id,
    ).first()

    if not attempt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attempt not found"
        )

    if not data.answers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one answer is required"
        )

    updated_rows = 0
    for item in data.answers:
        question = db.query(Question).filter(
            Question.question_id == item.question_id,
            Question.drive_id == attempt.drive_id,
        ).first()
        if not question:
            continue

        payload_json = getattr(question, "payload_json", None)
        parsed_payload = {}
        if payload_json:
            try:
                parsed_payload = json.loads(str(payload_json))
            except json.JSONDecodeError:
                parsed_payload = {}

        correct_answer = parsed_payload.get("correct_answer")
        question_type = str(getattr(question, "question_type", "MCQ") or "MCQ")
        is_correct = _answers_equal(correct_answer, item.answer, question_type)
        marks_obtained = int(getattr(question, "marks", 0) or 0) if is_correct else 0

        stored_answer = _to_storage_text(item.answer)

        row = db.query(Answer).filter(
            Answer.attempt_id == attempt_id,
            Answer.question_id == question.question_id,
        ).first()

        if row:
            row.selected_option = stored_answer
            row.marks_obtained = marks_obtained
        else:
            db.add(Answer(
                attempt_id=attempt_id,
                question_id=question.question_id,
                selected_option=stored_answer,
                marks_obtained=marks_obtained,
            ))
        updated_rows += 1

    total_marks = db.query(Answer).filter(Answer.attempt_id == attempt_id).all()
    attempt.total_marks = sum(int(a.marks_obtained or 0) for a in total_marks)

    db.commit()

    return {
        "message": "Answers saved",
        "attempt_id": attempt_id,
        "saved_answers": updated_rows,
        "total_marks": attempt.total_marks,
    }


@router.get("/exams/discover")
def discover_published_exams(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    candidate = _get_candidate_from_token(credentials, db)
    today = datetime.now().date()

    exams = (
        db.query(Drive, Vendor)
        .join(Vendor, Vendor.vendor_id == Drive.vendor_id)
        .filter(Drive.is_published == True)
        .order_by(Drive.created_at.desc())
        .all()
    )

    registered_ids = {
        row.drive_id
        for row in db.query(DriveRegistration).filter(DriveRegistration.candidate_id == candidate.candidate_id).all()
    }

    rows = []
    for exam, vendor in exams:
        is_test_completed = bool(exam.end_date and exam.end_date < today)
        section_count = db.query(ExamSection).filter(ExamSection.drive_id == exam.drive_id).count()
        rows.append(
            {
                "exam_id": exam.drive_id,
                "title": exam.title,
                "organization": vendor.company_name,
                "organization_type": vendor.organization_type,
                "exam_type": exam.exam_type,
                "duration_minutes": exam.duration_minutes,
                "max_attempts": exam.max_attempts,
                "description": exam.description,
                "generation_mode": exam.generation_mode or "static",
                "eligibility": exam.eligibility,
                "start_date": str(exam.start_date) if exam.start_date else None,
                "end_date": str(exam.end_date) if exam.end_date else None,
                "exam_date": exam.exam_date.isoformat() if exam.exam_date else None,
                "max_marks": exam.max_marks,
                "section_count": section_count,
                "key_topics": _parse_json_list(exam.key_topics),
                "specializations": _parse_json_list(exam.specializations),
                "registered": exam.drive_id in registered_ids,
                "is_test_completed": is_test_completed,
            }
        )

    return {"exams": rows}


@router.post("/exams/{exam_id}/register")
def register_for_exam(
    exam_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    candidate = _get_candidate_from_token(credentials, db)

    exam = db.query(Drive).filter(Drive.drive_id == exam_id, Drive.is_published == True).first()
    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Published exam not found"
        )

    existing = db.query(DriveRegistration).filter(
        DriveRegistration.drive_id == exam_id,
        DriveRegistration.candidate_id == candidate.candidate_id,
    ).first()

    if existing:
        active_code = _get_active_launch_code(db, candidate.candidate_id, exam_id)
        if not active_code:
            active_code = _issue_exam_launch_code(db, existing, candidate.candidate_id, exam_id)
            db.commit()

        return {
            "message": "Already registered",
            "registration_id": existing.registration_id,
            "exam_id": exam_id,
            "exam_launch_code": active_code.launch_code,
            "exam_launch_code_expires_at": active_code.expires_at.isoformat() if active_code.expires_at else None,
        }

    registration = DriveRegistration(
        drive_id=exam_id,
        candidate_id=candidate.candidate_id,
    )
    db.add(registration)
    db.commit()
    db.refresh(registration)

    morphing_dispatched = False
    morphing_request_id = None
    morphing_status = "skipped"

    _MORPHING_ELIGIBLE_MODES = {"static", "morphing"}
    exam_generation_mode = str(exam.generation_mode or "static").strip().lower()

    if exam_generation_mode in _MORPHING_ELIGIBLE_MODES:
        try:
            registration_payload = _build_registration_morph_payload(
                candidate_id=candidate.candidate_id,
                exam_id=exam_id,
            )
            morphing_dispatched, morphing_request_id, morphing_status = _dispatch_morphing_registration(registration_payload)
        except Exception:
            morphing_dispatched = False
            morphing_request_id = None
            morphing_status = "dispatch_failed"
    else:
        morphing_status = f"skipped_not_morphing_exam ({exam_generation_mode})"


    launch_code = _issue_exam_launch_code(db, registration, candidate.candidate_id, exam_id)
    db.commit()

    return {
        "message": "Registration successful",
        "registration_id": registration.registration_id,
        "exam_id": exam_id,
        "exam_launch_code": launch_code.launch_code,
        "exam_launch_code_expires_at": launch_code.expires_at.isoformat() if launch_code.expires_at else None,
        "morphing_dispatched": morphing_dispatched,
        "morphing_request_id": morphing_request_id,
        "morphing_status": morphing_status,
    }


@router.post("/exams/{exam_id}/launch-code")
def regenerate_exam_launch_code(
    exam_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    candidate = _get_candidate_from_token(credentials, db)

    registration = db.query(DriveRegistration).filter(
        DriveRegistration.drive_id == exam_id,
        DriveRegistration.candidate_id == candidate.candidate_id,
    ).first()
    if not registration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registration not found",
        )

    launch_code = _issue_exam_launch_code(db, registration, candidate.candidate_id, exam_id)
    db.commit()

    return {
        "message": "Exam launch code generated",
        "exam_id": exam_id,
        "registration_id": registration.registration_id,
        "exam_launch_code": launch_code.launch_code,
        "exam_launch_code_expires_at": launch_code.expires_at.isoformat() if launch_code.expires_at else None,
    }


@router.delete("/exams/{exam_id}/register")
def unregister_from_exam(
    exam_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    candidate = _get_candidate_from_token(credentials, db)

    registration = db.query(DriveRegistration).filter(
        DriveRegistration.drive_id == exam_id,
        DriveRegistration.candidate_id == candidate.candidate_id,
    ).first()

    if not registration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registration not found"
        )

    attempts = (
        db.query(ExamAttempt)
        .filter(
            ExamAttempt.drive_id == exam_id,
            ExamAttempt.candidate_id == candidate.candidate_id,
        )
        .all()
    )

    has_started_attempt = bool(attempts)
    has_completed_attempt = any(
        (str(getattr(attempt, "status", "") or "").strip().lower() == "submitted")
        or (getattr(attempt, "end_time", None) is not None)
        for attempt in attempts
    )

    if has_started_attempt and not has_completed_attempt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot unregister while an exam attempt is in progress",
        )

    launch_code_count = (
        db.query(ExamLaunchCode)
        .filter(ExamLaunchCode.registration_id == registration.registration_id)
        .count()
    )

    # Remove launch-code rows first to satisfy FK before deleting registration.
    if launch_code_count > 0:
        (
            db.query(ExamLaunchCode)
            .filter(ExamLaunchCode.registration_id == registration.registration_id)
            .delete(synchronize_session=False)
        )

    db.delete(registration)
    db.commit()

    if not has_started_attempt:
        message = "Unregistered successfully; pre-start registration row deleted"
    elif has_completed_attempt:
        message = "Unregistered successfully; completed-attempt registration archived and removed"
    else:
        message = "Unregistered successfully"

    return {
        "message": message,
        "exam_id": exam_id,
        "registration_id": registration.registration_id,
        "launch_code_count": launch_code_count,
        "attempt_started": has_started_attempt,
        "attempt_completed": has_completed_attempt,
        "unregistered": True,
    }


@router.get("/exams/upcoming")
def list_upcoming_registered_exams(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    candidate = _get_candidate_from_token(credentials, db)

    now = datetime.now()

    rows = (
        db.query(DriveRegistration, Drive, Vendor)
        .join(Drive, Drive.drive_id == DriveRegistration.drive_id)
        .join(Vendor, Vendor.vendor_id == Drive.vendor_id)
        .filter(
            DriveRegistration.candidate_id == candidate.candidate_id,
            Drive.is_published == True,
        )
        .order_by(Drive.exam_date.asc(), DriveRegistration.registered_at.desc())
        .all()
    )

    exams = []
    for registration, drive, vendor in rows:
        end_date = getattr(drive, "end_date", None)

        is_completed = bool(end_date and end_date < now.date())

        if is_completed:
            continue

        active_code = _get_active_launch_code(db, candidate.candidate_id, drive.drive_id)

        section_count = db.query(ExamSection).filter(ExamSection.drive_id == drive.drive_id).count()
        exams.append(
            {
                "registration_id": registration.registration_id,
                "registered_at": registration.registered_at.isoformat() if registration.registered_at else None,
                "exam_id": drive.drive_id,
                "title": drive.title,
                "organization": vendor.company_name,
                "organization_type": vendor.organization_type,
                "exam_type": drive.exam_type,
                "duration_minutes": drive.duration_minutes,
                "max_attempts": drive.max_attempts,
                "description": drive.description,
                "generation_mode": drive.generation_mode or "static",
                "eligibility": drive.eligibility,
                "start_date": str(drive.start_date) if drive.start_date else None,
                "end_date": str(drive.end_date) if drive.end_date else None,
                "exam_date": drive.exam_date.isoformat() if drive.exam_date else None,
                "max_marks": drive.max_marks,
                "section_count": section_count,
                "key_topics": _parse_json_list(drive.key_topics),
                "specializations": _parse_json_list(drive.specializations),
                "exam_launch_code": active_code.launch_code if active_code else None,
                "exam_launch_code_expires_at": active_code.expires_at.isoformat() if active_code and active_code.expires_at else None,
            }
        )

    return {"exams": exams}


@router.get("/history/results")
def list_candidate_history_results(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    candidate = _get_candidate_from_token(credentials, db)

    rows = (
        db.query(ExamResult, Drive)
        .join(Drive, Drive.drive_id == ExamResult.drive_id)
        .filter(
            ExamResult.candidate_id == candidate.candidate_id,
            ExamResult.published_to_candidate == True,
        )
        .order_by(ExamResult.published_at.desc(), ExamResult.evaluated_at.desc())
        .all()
    )

    history: list[dict] = []
    for result, drive in rows:
        status_raw = str(result.result_status or "pending_eval").strip().lower()
        if status_raw in {"pass", "passed"}:
            status_label = "Pass"
            offer_download_url = f"/candidate/offers/{int(result.result_id)}/download"
        elif status_raw in {"fail", "failed"}:
            status_label = "Fail"
            offer_download_url = None
        else:
            status_label = "Pending Eval"
            offer_download_url = None

        report_url = _create_signed_storage_url(
            bucket=str(getattr(result, "report_pdf_bucket", "") or ""),
            object_path=str(getattr(result, "report_pdf_path", "") or ""),
            expires_in=REPORT_LINK_TTL_SECONDS,
        )

        history.append(
            {
                "result_id": int(result.result_id),
                "exam_id": int(drive.drive_id),
                "title": drive.title,
                "score": float(result.score) if result.score is not None else None,
                "status": status_label,
                "rank": result.rank,
                "date": result.evaluated_at.isoformat() if result.evaluated_at else None,
                "report_url": report_url,
                "offer_download_url": offer_download_url,
            }
        )

    return {"history": history}


@router.get("/offers/{result_id}/download")
def download_dummy_offer_pdf(
    result_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    candidate = _get_candidate_from_token(credentials, db)

    result = (
        db.query(ExamResult)
        .filter(
            ExamResult.result_id == result_id,
            ExamResult.candidate_id == candidate.candidate_id,
            ExamResult.published_to_candidate == True,
        )
        .first()
    )
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Offer not available")

    status_raw = str(getattr(result, "result_status", "") or "").strip().lower()
    if status_raw not in {"pass", "passed"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Offer available only for passed candidates")

    existing_offer = (
        db.query(Offer)
        .filter(Offer.drive_id == result.drive_id, Offer.candidate_id == candidate.candidate_id)
        .first()
    )
    if not existing_offer:
        existing_offer = Offer(
            drive_id=result.drive_id,
            candidate_id=candidate.candidate_id,
            offer_status="issued",
            generated_at=datetime.utcnow(),
        )
        db.add(existing_offer)
    else:
        existing_offer.offer_status = "issued"
        existing_offer.generated_at = datetime.utcnow()

    db.commit()

    return Response(
        content=_DUMMY_OFFER_PDF,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="offer-letter.pdf"'},
    )