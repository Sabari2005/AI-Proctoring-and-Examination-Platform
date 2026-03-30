from sqlalchemy import (
    Column, Integer, String, Boolean,
    ForeignKey, Date, DateTime, Text,
    Numeric, Enum, JSON
)
from sqlalchemy.sql import func
from .database import Base
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import relationship
import enum

class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)

    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String, nullable=False)

    role = Column(String(20), nullable=False)  # admin / vendor / candidate

    is_active = Column(Boolean, default=True)
    email_verified = Column(Boolean, default=False)

    created_at = Column(DateTime, server_default=func.now())

class Vendor(Base):
    __tablename__ = "vendors"

    vendor_id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)

    company_name = Column(String(255), nullable=False)
    organization_type = Column(String(100))
    organization_email = Column(String(255))
    description = Column(Text)

    website = Column(String)
    logo_url = Column(String)

    created_at = Column(DateTime, server_default=func.now())

class Candidate(Base):
    __tablename__ = "candidates"

    candidate_id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    user = relationship("User")
    full_name = Column(String(255), nullable=False)

    mobile_no = Column(String(20))
    country = Column(String(100))
    timezone = Column(String(100))

    photo_url = Column(String)

    years_of_experience = Column(Integer, default=0)

    onboarding_step = Column(Integer, default=0)  # ← track onboarding progress

    created_at = Column(DateTime, server_default=func.now())

class CandidateIdentity(Base):
    __tablename__ = "candidate_identities"

    identity_id = Column(Integer, primary_key=True)

    candidate_id = Column(Integer, ForeignKey("candidates.candidate_id"))

    id_type = Column(String(50))   # aadhaar / passport
    id_number = Column(String(50))

    id_document_url = Column(String)

    verified = Column(Boolean, default=False)

    created_at = Column(DateTime, server_default=func.now())

class Education(Base):
    __tablename__ = "educations"

    education_id = Column(Integer, primary_key=True)

    candidate_id = Column(Integer, ForeignKey("candidates.candidate_id"))

    education_level = Column(String(100))  # B.Tech / M.Tech / MBA
    university = Column(String(255))

    specialization = Column(String(255))

    graduation_year = Column(Integer)

    cgpa = Column(Numeric(3,2))

    created_at = Column(DateTime, server_default=func.now())

class Skill(Base):
    __tablename__ = "skills"

    skill_id = Column(Integer, primary_key=True)

    candidate_id = Column(Integer, ForeignKey("candidates.candidate_id"), nullable=False)

    skill_name = Column(String(100), nullable=False)

class CandidateDocument(Base):
    __tablename__ = "candidate_documents"

    document_id = Column(Integer, primary_key=True)

    candidate_id = Column(Integer, ForeignKey("candidates.candidate_id"), nullable=False)

    document_type = Column(String(50), nullable=False)
    # resume / photo / aadhaar

    file_url = Column(String, nullable=False)

    uploaded_at = Column(DateTime, server_default=func.now())


class CandidateLink(Base):
    __tablename__ = "candidate_links"

    link_id = Column(Integer, primary_key=True)

    candidate_id = Column(Integer, ForeignKey("candidates.candidate_id"))

    linkedin = Column(String)
    github = Column(String)
    personal_website = Column(String)

class Drive(Base):
    __tablename__ = "drives"

    drive_id = Column(Integer, primary_key=True)

    vendor_id = Column(Integer, ForeignKey("vendors.vendor_id"))

    title = Column(String(255), nullable=False)

    description = Column(Text)

    eligibility = Column(Text)

    start_date = Column(Date)
    end_date = Column(Date)

    exam_date = Column(DateTime)

    duration_minutes = Column(Integer)
    max_attempts = Column(Integer, default=1)
    exam_type = Column(String(100))
    generation_mode = Column(String(20), default="static")
    is_published = Column(Boolean, default=False)
    key_topics = Column(Text)
    specializations = Column(Text)

    max_marks = Column(Integer)

    status = Column(String(20), default="open")

    created_at = Column(DateTime, server_default=func.now())


class ExamSection(Base):
    __tablename__ = "exam_sections"

    section_id = Column(Integer, primary_key=True, index=True)
    drive_id = Column(Integer, ForeignKey("drives.drive_id"), nullable=False)

    title = Column(String(255), nullable=False)
    section_type = Column(String(50), default="mixed")
    question_type = Column(String(30), default="mcq")
    order_index = Column(Integer, default=1)
    planned_question_count = Column(Integer, default=0)
    marks_weight = Column(Integer)
    status = Column(String(20), default="draft")

    created_at = Column(DateTime, server_default=func.now())

class DriveRegistration(Base):
    __tablename__ = "drive_registrations"

    registration_id = Column(Integer, primary_key=True)

    drive_id = Column(Integer, ForeignKey("drives.drive_id"), nullable=False)
    candidate_id = Column(Integer, ForeignKey("candidates.candidate_id"), nullable=False)

    registered_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("drive_id", "candidate_id", name="unique_drive_registration"),
    )


class ExamLaunchCode(Base):
    __tablename__ = "exam_launch_codes"

    launch_id = Column(Integer, primary_key=True)
    registration_id = Column(Integer, ForeignKey("drive_registrations.registration_id"), nullable=False)
    drive_id = Column(Integer, ForeignKey("drives.drive_id"), nullable=False)
    candidate_id = Column(Integer, ForeignKey("candidates.candidate_id"), nullable=False)

    launch_code = Column(String(64), unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())

class Question(Base):
    __tablename__ = "questions"

    question_id = Column(Integer, primary_key=True)

    drive_id = Column(Integer, ForeignKey("drives.drive_id"))
    section_id = Column(Integer, ForeignKey("exam_sections.section_id"))
    question_type = Column(String(30), default="MCQ")
    payload_json = Column(Text)

    question_text = Column(Text)

    option_a = Column(Text)
    option_b = Column(Text)
    option_c = Column(Text)
    option_d = Column(Text)

    correct_option = Column(Text)
    taxonomy_level = Column(Integer, default=3, nullable=False)
    morphing_strategy = Column(String(80))
    time_complexity = Column(String(120))
    space_complexity = Column(String(120))

    marks = Column(Integer)

class Answer(Base):
    __tablename__ = "answers"

    answer_id = Column(Integer, primary_key=True)

    attempt_id = Column(Integer, ForeignKey("exam_attempts.attempt_id"))

    question_id = Column(Integer, ForeignKey("questions.question_id"))

    selected_option = Column(Text)

    marks_obtained = Column(Integer)


class JitSectionSession(Base):
    __tablename__ = "jit_section_sessions"

    jit_section_session_id = Column(Integer, primary_key=True, index=True)
    attempt_id = Column(Integer, ForeignKey("exam_attempts.attempt_id"), nullable=False)
    section_id = Column(Integer, ForeignKey("exam_sections.section_id"), nullable=False)
    section_order = Column(Integer, nullable=False)
    section_title = Column(String(255), nullable=False)
    question_type = Column(String(30), default="mcq")
    planned_question_count = Column(Integer, default=0)
    asked_count = Column(Integer, default=0)
    jit_session_id = Column(String(100))
    current_question_payload = Column(JSON)
    status = Column(String(20), default="pending")
    final_report = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class JitAnswerEvent(Base):
    __tablename__ = "jit_answer_events"

    jit_answer_event_id = Column(Integer, primary_key=True, index=True)
    attempt_id = Column(Integer, ForeignKey("exam_attempts.attempt_id"), nullable=False)
    jit_section_session_id = Column(Integer, ForeignKey("jit_section_sessions.jit_section_session_id"), nullable=False)
    question_id = Column(String(120), nullable=False)
    question_number = Column(Integer, nullable=False)
    question_payload = Column(JSON)
    submitted_answer = Column(Text)
    time_taken_seconds = Column(Integer, default=0)
    confidence = Column(Integer)
    evaluation = Column(JSON)
    adaptive_decision = Column(JSON)
    score = Column(Integer, default=0)
    is_correct = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

class Offer(Base):
    __tablename__ = "offers"

    offer_id = Column(Integer, primary_key=True)

    drive_id = Column(Integer, ForeignKey("drives.drive_id"))
    candidate_id = Column(Integer, ForeignKey("candidates.candidate_id"))

    offer_status = Column(String(20), default="pending")
    offer_pdf_bucket = Column(String(100))
    offer_pdf_path = Column(Text)
    generated_at = Column(DateTime)

    published_at = Column(DateTime, server_default=func.now())

class ExamAttempt(Base):
    __tablename__ = "exam_attempts"

    attempt_id = Column(Integer, primary_key=True, index=True)

    drive_id = Column(Integer, ForeignKey("drives.drive_id"), nullable=False)
    candidate_id = Column(Integer, ForeignKey("candidates.candidate_id"), nullable=False)

    start_time = Column(DateTime)
    end_time = Column(DateTime)

    total_marks = Column(Integer, default=0)

    status = Column(String(20), default="started")
    # started / submitted / terminated

    created_at = Column(DateTime, server_default=func.now())


class ExamResult(Base):
    __tablename__ = "exam_results"

    result_id = Column(Integer, primary_key=True, index=True)

    drive_id = Column(Integer, ForeignKey("drives.drive_id"), nullable=False)
    candidate_id = Column(Integer, ForeignKey("candidates.candidate_id"), nullable=False)
    attempt_id = Column(Integer, ForeignKey("exam_attempts.attempt_id"), nullable=False)

    score = Column(Numeric(8, 2))
    rank = Column(Integer)
    result_status = Column(String(20), default="pending_eval")

    published_to_candidate = Column(Boolean, default=False)
    published_at = Column(DateTime)
    evaluated_at = Column(DateTime)

    report_json_path = Column(Text)
    report_json_bucket = Column(String(100))
    report_json_uploaded_at = Column(DateTime)
    report_preview_status = Column(String(30), default="pending")
    report_pdf_bucket = Column(String(100))
    report_pdf_path = Column(Text)
    report_html_url = Column(Text)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("drive_id", "candidate_id", name="uq_exam_results_drive_candidate"),
        UniqueConstraint("attempt_id", name="uq_exam_results_attempt"),
    )


class Notification(Base):
    __tablename__ = "notifications"

    notification_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())


# ──────── CODING QUESTIONS MODELS ──────────

class CodeSubmissionStatus(str, enum.Enum):
    """Status enum for code submissions."""
    PENDING = "pending"
    RUNNING = "running"
    ACCEPTED = "accepted"
    WRONG_ANSWER = "wrong_answer"
    TIME_LIMIT_EXCEEDED = "time_limit_exceeded"
    MEMORY_LIMIT_EXCEEDED = "memory_limit_exceeded"
    RUNTIME_ERROR = "runtime_error"
    COMPILATION_ERROR = "compilation_error"
    SYSTEM_ERROR = "system_error"


class CodingQuestion(Base):
    """Extended question details for coding challenges."""
    __tablename__ = "coding_questions"

    coding_question_id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.question_id"), 
                        nullable=False, unique=True, index=True)

    problem_statement = Column(Text, nullable=False)
    difficulty = Column(String(20), default="medium")  # easy, medium, hard
    constraints = Column(Text)

    supported_languages = Column(JSON, default=list)  # ["python", "javascript", ...]
    starter_code = Column(JSON, default=dict)  # {python: "def solve():\n    pass", ...}
    examples = Column(JSON, default=list)  # [{input: "...", output: "...", explanation: "..."}]

    execution_time_limit_seconds = Column(Integer, default=10)
    memory_limit_mb = Column(Integer, default=256)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class TestCase(Base):
    """Test cases for coding questions."""
    __tablename__ = "test_cases"

    test_case_id = Column(Integer, primary_key=True, index=True)
    coding_question_id = Column(Integer, ForeignKey("coding_questions.coding_question_id"),
                               nullable=False, index=True)

    input_data = Column(Text, nullable=False)
    expected_output = Column(Text, nullable=False)

    is_sample = Column(Boolean, default=False)  # Show to candidate during exam
    explanation = Column(Text)
    is_hidden = Column(Boolean, default=True)  # Hidden test cases for final grading

    created_at = Column(DateTime, server_default=func.now())


class CodeSubmission(Base):
    """Student's code submissions for coding questions."""
    __tablename__ = "code_submissions"

    submission_id = Column(Integer, primary_key=True, index=True)
    attempt_id = Column(Integer, ForeignKey("exam_attempts.attempt_id"), 
                       nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("questions.question_id"), 
                        nullable=False, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.candidate_id"), 
                         nullable=False, index=True)

    language = Column(String(32), nullable=False)  # python, javascript, java, cpp, go, rust
    source_code = Column(Text, nullable=False)

    status = Column(String(50), default="pending")
    test_results = Column(JSON, default=list)  # [{test_case_id, passed, actual_output, expected_output, ...}]

    passed_test_cases = Column(Integer, default=0)
    total_test_cases = Column(Integer, default=0)

    execution_time_ms = Column(Integer)
    memory_used_kb = Column(Integer)

    error_message = Column(Text)
    stdout = Column(Text)
    stderr = Column(Text)

    marks_obtained = Column(Integer, default=0)
    is_final = Column(Boolean, default=False)

    submitted_at = Column(DateTime, server_default=func.now())
    executed_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())