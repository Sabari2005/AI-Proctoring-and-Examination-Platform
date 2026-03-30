from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.sql import func

from server.db import Base


class Candidate(Base):
    __tablename__ = "candidates"

    candidate_id = Column(Integer, primary_key=True)


class Drive(Base):
    __tablename__ = "drives"

    drive_id = Column(Integer, primary_key=True)
    is_published = Column(Boolean)


class DriveRegistration(Base):
    __tablename__ = "drive_registrations"

    registration_id = Column(Integer, primary_key=True)
    drive_id = Column(Integer, ForeignKey("drives.drive_id"), nullable=False)
    candidate_id = Column(Integer, ForeignKey("candidates.candidate_id"), nullable=False)


class ExamSection(Base):
    __tablename__ = "exam_sections"

    section_id = Column(Integer, primary_key=True)
    drive_id = Column(Integer, ForeignKey("drives.drive_id"), nullable=False)
    title = Column(String(255), nullable=False)
    order_index = Column(Integer)


class Question(Base):
    __tablename__ = "questions"

    question_id = Column(Integer, primary_key=True)
    drive_id = Column(Integer, ForeignKey("drives.drive_id"))
    section_id = Column(Integer, ForeignKey("exam_sections.section_id"))
    question_type = Column(String(30))
    payload_json = Column(Text)
    question_text = Column(Text)
    option_a = Column(Text)
    option_b = Column(Text)
    option_c = Column(Text)
    option_d = Column(Text)
    correct_option = Column(Text)
    taxonomy_level = Column(Integer)
    morphing_strategy = Column(String(80))
    time_complexity = Column(String(120))
    space_complexity = Column(String(120))
    marks = Column(Integer)


class LLMRegistrationJob(Base):
    __tablename__ = "llm_registration_jobs"

    job_id = Column(Integer, primary_key=True)
    candidate_id = Column(Integer, ForeignKey("candidates.candidate_id"), nullable=False)
    exam_id = Column(Integer, ForeignKey("drives.drive_id"), nullable=False)
    status = Column(String(30), nullable=False, default="queued")
    processed_questions = Column(Integer, nullable=False, default=0)
    created_variants = Column(Integer, nullable=False, default=0)
    error_message = Column(Text)
    started_at = Column(DateTime, server_default=func.now(), nullable=False)
    finished_at = Column(DateTime)

    __table_args__ = (
        UniqueConstraint("candidate_id", "exam_id", name="uq_llm_registration_jobs_candidate_exam"),
    )


class LLMQuestionVariant(Base):
    __tablename__ = "llm_question_variants"

    variant_id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey("llm_registration_jobs.job_id"), nullable=False)
    candidate_id = Column(Integer, ForeignKey("candidates.candidate_id"), nullable=False)
    exam_id = Column(Integer, ForeignKey("drives.drive_id"), nullable=False)
    section_id = Column(Integer, ForeignKey("exam_sections.section_id"), nullable=False)
    source_question_id = Column(Integer, ForeignKey("questions.question_id"), nullable=False)
    source_question_type = Column(String(50), nullable=False)
    variant_index = Column(Integer, nullable=False)
    morph_type = Column(String(100))
    trace_id = Column(String(64))
    semantic_score = Column(Float)
    difficulty_actual = Column(String(64))
    selected_for_exam = Column(Boolean, default=True, nullable=False)
    payload_json = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "candidate_id",
            "exam_id",
            "source_question_id",
            "variant_index",
            name="uq_llm_question_variants_candidate_exam_question_variant",
        ),
    )
