"""
app/core/qtype_schemas.py
──────────────────────────
Pydantic input/output schemas for all 5 new question types.
Drop into app/core/ alongside existing schemas.py.

Design principle per type:
  FIB        — blank positions + correct_answers list + tolerance
  Short      — model_answer + keywords + grading_rubric
  MSQ        — options + correct_answers (list) + partial_credit rules
  Numerical  — correct_value (float) + unit + tolerance
  Long       — rubric (list of points+marks) + word_limit + no single answer
"""
from typing import Optional, Any, Union
from pydantic import BaseModel, Field, model_validator
from .qtype_enums import (
    QType, AnswerTolerance, ToleranceType,
    FIBMorphStrategy, ShortMorphStrategy,
    MSQMorphStrategy, NumericalMorphStrategy, LongMorphStrategy,
)
from .enums import DifficultyLevel, BloomLevel


# ═══════════════════════════════════════════════════════════════════════════════
#  FILL IN THE BLANK
# ═══════════════════════════════════════════════════════════════════════════════

class FIBMorphConfig(BaseModel):
    strategies: list[FIBMorphStrategy] = [FIBMorphStrategy.REPHRASE]
    variant_count: int = Field(default=1, ge=1, le=5)
    target_difficulty: Optional[DifficultyLevel] = None
    bloom_target: Optional[BloomLevel] = None


class FIBInput(BaseModel):
    section: str
    question: str = Field(..., description="Question text with ________ as blank marker")
    blank_positions: list[int] = Field(default_factory=list)
    correct_answers: list[str] = Field(..., min_length=1)
    answer_tolerance: AnswerTolerance = AnswerTolerance.CASE_INSENSITIVE
    hint: Optional[str] = None
    difficulty: DifficultyLevel = DifficultyLevel.MEDIUM
    morph_config: FIBMorphConfig = Field(default_factory=FIBMorphConfig)

    @model_validator(mode="after")
    def blank_marker_present(self):
        if "________" not in self.question and "____" not in self.question:
            raise ValueError("FIB question must contain '________' as blank marker.")
        return self


class MorphedFIB(BaseModel):
    question: str
    blank_positions: list[int]
    correct_answers: list[str]
    answer_tolerance: AnswerTolerance
    hint: Optional[str]
    morph_type: FIBMorphStrategy
    difficulty_actual: DifficultyLevel
    semantic_score: float
    answer_changed: bool = False
    quality_flags: list[str] = Field(default_factory=list)
    explanation: str = ""


class FIBMorphOutput(BaseModel):
    trace_id: str
    original_question: str
    section: str
    qtype: QType = QType.FIB
    variants: list[MorphedFIB]
    total_variants: int = 0

    @model_validator(mode="after")
    def set_total(self):
        self.total_variants = len(self.variants)
        return self


# ═══════════════════════════════════════════════════════════════════════════════
#  SHORT ANSWER
# ═══════════════════════════════════════════════════════════════════════════════

class GradingRubric(BaseModel):
    keywords_required: int = 0
    sentence_limit: Optional[int] = None
    partial_credit: bool = True
    marks: int = 10


class ShortMorphConfig(BaseModel):
    strategies: list[ShortMorphStrategy] = [ShortMorphStrategy.REPHRASE]
    variant_count: int = Field(default=1, ge=1, le=5)
    target_difficulty: Optional[DifficultyLevel] = None
    bloom_target: Optional[BloomLevel] = None


class ShortInput(BaseModel):
    section: str
    question: str = Field(..., min_length=10)
    model_answer: str = Field(..., min_length=5)
    keywords: list[str] = Field(default_factory=list)
    min_words: int = Field(default=10, ge=1)
    max_words: int = Field(default=100, ge=10)
    grading_rubric: GradingRubric = Field(default_factory=GradingRubric)
    difficulty: DifficultyLevel = DifficultyLevel.MEDIUM
    morph_config: ShortMorphConfig = Field(default_factory=ShortMorphConfig)


class MorphedShort(BaseModel):
    question: str
    model_answer: str
    keywords: list[str]
    min_words: int
    max_words: int
    grading_rubric: GradingRubric
    morph_type: ShortMorphStrategy
    difficulty_actual: DifficultyLevel
    semantic_score: float
    answer_changed: bool = False
    quality_flags: list[str] = Field(default_factory=list)
    explanation: str = ""


class ShortMorphOutput(BaseModel):
    trace_id: str
    original_question: str
    section: str
    qtype: QType = QType.SHORT
    variants: list[MorphedShort]
    total_variants: int = 0

    @model_validator(mode="after")
    def set_total(self):
        self.total_variants = len(self.variants)
        return self


# ═══════════════════════════════════════════════════════════════════════════════
#  MULTIPLE SELECT QUESTION (MSQ)
# ═══════════════════════════════════════════════════════════════════════════════

class MSQMorphConfig(BaseModel):
    strategies: list[MSQMorphStrategy] = [MSQMorphStrategy.REPHRASE]
    variant_count: int = Field(default=1, ge=1, le=5)
    target_difficulty: Optional[DifficultyLevel] = None
    bloom_target: Optional[BloomLevel] = None


class MSQInput(BaseModel):
    section: str
    question: str = Field(..., min_length=10)
    options: list[str] = Field(..., min_length=4, max_length=8)
    correct_answers: list[str] = Field(..., min_length=1)
    min_correct: int = Field(default=1, ge=1)
    max_correct: Optional[int] = None
    partial_credit: bool = True
    penalty_for_wrong: bool = False
    difficulty: DifficultyLevel = DifficultyLevel.MEDIUM
    morph_config: MSQMorphConfig = Field(default_factory=MSQMorphConfig)

    @model_validator(mode="after")
    def correct_answers_in_options(self):
        for ans in self.correct_answers:
            if ans not in self.options:
                raise ValueError(f"correct_answer '{ans}' not in options.")
        if len(self.correct_answers) < 2:
            raise ValueError("MSQ requires at least 2 correct answers.")
        return self


class MorphedMSQ(BaseModel):
    question: str
    options: list[str]
    correct_answers: list[str]
    partial_credit: bool
    penalty_for_wrong: bool
    morph_type: MSQMorphStrategy
    difficulty_actual: DifficultyLevel
    semantic_score: float
    answer_changed: bool = False
    quality_flags: list[str] = Field(default_factory=list)
    explanation: str = ""


class MSQMorphOutput(BaseModel):
    trace_id: str
    original_question: str
    section: str
    qtype: QType = QType.MSQ
    variants: list[MorphedMSQ]
    total_variants: int = 0

    @model_validator(mode="after")
    def set_total(self):
        self.total_variants = len(self.variants)
        return self


# ═══════════════════════════════════════════════════════════════════════════════
#  NUMERICAL
# ═══════════════════════════════════════════════════════════════════════════════

class NumericalMorphConfig(BaseModel):
    strategies: list[NumericalMorphStrategy] = [NumericalMorphStrategy.REPHRASE]
    variant_count: int = Field(default=1, ge=1, le=5)
    target_difficulty: Optional[DifficultyLevel] = None
    bloom_target: Optional[BloomLevel] = None


class NumericalInput(BaseModel):
    section: str
    question: str = Field(..., min_length=10)
    correct_value: float
    unit: str = ""
    tolerance: float = Field(default=0.0, ge=0.0)
    tolerance_type: ToleranceType = ToleranceType.EXACT
    decimal_places: int = Field(default=2, ge=0)
    formula: str = ""
    difficulty: DifficultyLevel = DifficultyLevel.MEDIUM
    morph_config: NumericalMorphConfig = Field(default_factory=NumericalMorphConfig)


class MorphedNumerical(BaseModel):
    question: str
    correct_value: float
    unit: str
    tolerance: float
    tolerance_type: ToleranceType
    decimal_places: int
    formula: str
    morph_type: NumericalMorphStrategy
    difficulty_actual: DifficultyLevel
    semantic_score: float
    answer_changed: bool = False
    quality_flags: list[str] = Field(default_factory=list)
    explanation: str = ""


class NumericalMorphOutput(BaseModel):
    trace_id: str
    original_question: str
    section: str
    qtype: QType = QType.NUMERICAL
    variants: list[MorphedNumerical]
    total_variants: int = 0

    @model_validator(mode="after")
    def set_total(self):
        self.total_variants = len(self.variants)
        return self


# ═══════════════════════════════════════════════════════════════════════════════
#  LONG ANSWER
# ═══════════════════════════════════════════════════════════════════════════════

class RubricPoint(BaseModel):
    point: str
    marks: int
    keywords: list[str] = Field(default_factory=list)


class Rubric(BaseModel):
    points: list[RubricPoint]
    total_marks: int
    min_areas: int = Field(default=1, ge=1)

    @model_validator(mode="after")
    def total_marks_matches(self):
        calculated = sum(p.marks for p in self.points)
        if calculated != self.total_marks:
            self.total_marks = calculated
        return self


class WordLimit(BaseModel):
    min: int = 100
    max: int = 800


class LongMorphConfig(BaseModel):
    strategies: list[LongMorphStrategy] = [LongMorphStrategy.REPHRASE]
    variant_count: int = Field(default=1, ge=1, le=5)
    target_difficulty: Optional[DifficultyLevel] = None
    bloom_target: Optional[BloomLevel] = None


class LongInput(BaseModel):
    section: str
    question: str = Field(..., min_length=20)
    rubric: Rubric
    word_limit: WordLimit = Field(default_factory=WordLimit)
    requires_examples: bool = False
    requires_diagrams: bool = False
    difficulty: DifficultyLevel = DifficultyLevel.HARD
    morph_config: LongMorphConfig = Field(default_factory=LongMorphConfig)

    @model_validator(mode="after")
    def rubric_has_points(self):
        if len(self.rubric.points) < 1:
            raise ValueError("Long answer rubric must have at least 1 point.")
        return self


class MorphedLong(BaseModel):
    question: str
    rubric: Rubric
    word_limit: WordLimit
    requires_examples: bool
    morph_type: LongMorphStrategy
    difficulty_actual: DifficultyLevel
    semantic_score: float
    answer_changed: bool = False
    quality_flags: list[str] = Field(default_factory=list)
    explanation: str = ""


class LongMorphOutput(BaseModel):
    trace_id: str
    original_question: str
    section: str
    qtype: QType = QType.LONG
    variants: list[MorphedLong]
    total_variants: int = 0

    @model_validator(mode="after")
    def set_total(self):
        self.total_variants = len(self.variants)
        return self