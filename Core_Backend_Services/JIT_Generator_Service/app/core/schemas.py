"""
JIT/app/core/schemas.py
────────────────────────
All Pydantic models for the JIT adaptive assessment engine.
"""
from typing import Optional, Any, Union
from pydantic import BaseModel, Field, model_validator
from .enums import QType, DifficultyLevel, BloomLevel, SkillLabel, AnswerStatus


# ── Session init ──────────────────────────────────────────────────────────────

class JITSessionConfig(BaseModel):
    section_topic: str = Field(..., description="e.g. 'Operating Systems', 'Python Basics'")
    num_questions: int = Field(..., ge=1, le=50)
    question_type: QType = QType.MCQ
    start_difficulty: DifficultyLevel = DifficultyLevel.EASY
    candidate_id: str = "anonymous"
    language: str = "en"
    # Sub-topics to cover (auto-extracted from section_topic if empty)
    sub_topics: list[str] = Field(default_factory=list)
    # Learning rate for theta updates — higher = faster adaptation
    learning_rate: float = Field(default=0.4, ge=0.1, le=1.0)


# ── Generated question (type-agnostic wrapper) ────────────────────────────────

class GeneratedQuestion(BaseModel):
    question_id: str
    session_id: str
    question_number: int              # 1-indexed
    qtype: QType
    difficulty: DifficultyLevel
    bloom_level: BloomLevel
    sub_topic: str
    question_text: str
    # MCQ / MSQ fields
    options: list[str] = Field(default_factory=list)
    correct_answers: list[str] = Field(default_factory=list)
    # FIB fields
    blank_positions: list[int] = Field(default_factory=list)
    # Numerical fields
    correct_value: Optional[float] = None
    unit: str = ""
    tolerance: float = 0.0
    # Short / Long fields
    model_answer: str = ""
    keywords: list[str] = Field(default_factory=list)
    word_limit: Optional[dict] = None
    rubric: Optional[dict] = None
    # Coding fields
    function_signature: str = ""
    test_cases: dict = Field(default_factory=dict)
    # Timing
    expected_time_seconds: int = 60
    # Meta
    hints: list[str] = Field(default_factory=list)


# ── Answer submission ─────────────────────────────────────────────────────────

# class AnswerSubmission(BaseModel):
#     session_id: str
#     question_id: str
#     question_number: int
#     answer: Any                        # str | list[str] | float | dict
#     time_taken_seconds: int = Field(..., ge=0)
#     confidence: Optional[int] = Field(None, ge=1, le=5)

class AnswerSubmission(BaseModel):
    session_id: str
    question_id: str
    question_number: int
    answer: Any                        # str | list[str] | float | dict
    time_taken_seconds: int = Field(..., ge=0)
    confidence: Optional[int] = Field(None, ge=1, le=5)
    language: str = "python" 


# ── Evaluation result ─────────────────────────────────────────────────────────

class EvaluationResult(BaseModel):
    question_id: str
    status: AnswerStatus
    score: float = Field(ge=0.0, le=1.0)
    correctness: float = Field(ge=0.0, le=1.0)   # alias of score for clarity
    time_ratio: float                              # actual / expected
    time_bonus: float
    confidence_score: float = 0.5
    streak_bonus: float = 0.0
    performance_score: float = 0.0
    feedback: str = ""
    correct_answer_reveal: Any = None


# ── Adaptive decision ─────────────────────────────────────────────────────────

class AdaptiveDecision(BaseModel):
    prev_theta: float
    new_theta: float
    theta_delta: float
    next_difficulty: DifficultyLevel
    next_sub_topic: str
    next_qtype: QType
    streak: int
    reason: str = ""


# ── Per-question record (stored in session history) ───────────────────────────

class QuestionRecord(BaseModel):
    question: GeneratedQuestion
    submission: AnswerSubmission
    evaluation: EvaluationResult
    decision: AdaptiveDecision


# ── Session state (the full running state) ────────────────────────────────────

class JITSessionState(BaseModel):
    session_id: str
    config: JITSessionConfig
    status: str = "active"            # active | completed | abandoned

    # Progress
    questions_asked: int = 0
    question_history: list[QuestionRecord] = Field(default_factory=list)
    seen_question_texts: list[str] = Field(default_factory=list)

    # Adaptive state
    theta: float = 2.0                # starts at Easy
    current_difficulty: DifficultyLevel = DifficultyLevel.EASY
    current_sub_topic: str = ""
    current_qtype: QType = QType.MCQ
    streak: int = 0
    consecutive_wrong: int = 0

    # Sub-topic tracking
    sub_topic_queue: list[str] = Field(default_factory=list)
    sub_topic_mastery: dict[str, float] = Field(default_factory=dict)

    # Current question (waiting for answer)
    pending_question: Optional[GeneratedQuestion] = None

    # Skill profile (updated after each answer)
    bloom_levels_reached: list[BloomLevel] = Field(default_factory=list)
    difficulty_trajectory: list[int] = Field(default_factory=list)

    # Final report (populated at end)
    final_report: Optional[dict] = None


# ── API response wrappers ─────────────────────────────────────────────────────

class StartSessionResponse(BaseModel):
    session_id: str
    first_question: GeneratedQuestion
    session_info: dict


class SubmitAnswerResponse(BaseModel):
    evaluation: EvaluationResult
    adaptive_decision: AdaptiveDecision
    next_question: Optional[GeneratedQuestion] = None
    session_complete: bool = False
    final_report: Optional[dict] = None


# ── Final report ──────────────────────────────────────────────────────────────

class FinalReport(BaseModel):
    session_id: str
    candidate_id: str
    section_topic: str
    total_questions: int
    correct: int
    partial: int
    wrong: int
    accuracy: float
    theta_final: float
    skill_label: SkillLabel
    highest_bloom: BloomLevel
    difficulty_trajectory: list[int]
    sub_topic_mastery: dict[str, float]
    sub_topic_attempts: dict[str, int] = Field(default_factory=dict)
    avg_time_ratio: float
    speed_profile: str               # "fast" | "normal" | "slow"
    strengths: list[str]
    weaknesses: list[str]
    recommendations: list[str]
    question_summary: list[dict]