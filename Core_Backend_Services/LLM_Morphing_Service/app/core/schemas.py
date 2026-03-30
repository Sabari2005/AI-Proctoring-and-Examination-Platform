from typing import Optional
from pydantic import BaseModel, Field, model_validator
from .enums import MorphStrategy, QuestionType, DifficultyLevel


# ── Input ────────────────────────────────────────────────────────────────────

class MorphConfig(BaseModel):
    strategies: list[MorphStrategy] = Field(
        default=[MorphStrategy.REPHRASE],
        description="Which morph strategies to apply"
    )
    variant_count: int = Field(default=1, ge=1, le=5)
    preserve_answer: bool = Field(default=True)
    target_difficulty: Optional[DifficultyLevel] = None
    preserve_format: bool = Field(default=True)

    @model_validator(mode="after")
    def validate_difficulty_with_strategy(self):
        if MorphStrategy.DIFFICULTY in self.strategies and self.target_difficulty is None:
            self.target_difficulty = DifficultyLevel.HARD
        return self


class MorphInput(BaseModel):
    section: str = Field(..., description="e.g. Aptitude, Verbal, Logical")
    question: str = Field(..., min_length=10)
    options: list[str] = Field(..., min_length=2, max_length=6)
    correct_answer: str = Field(..., description="Must match one of the options exactly")
    question_type: QuestionType = Field(default=QuestionType.MCQ)
    difficulty: DifficultyLevel = Field(default=DifficultyLevel.MEDIUM)
    morph_config: MorphConfig = Field(default_factory=MorphConfig)

    @model_validator(mode="after")
    def correct_answer_in_options(self):
        if self.correct_answer not in self.options:
            raise ValueError(
                f"correct_answer '{self.correct_answer}' must be one of the options"
            )
        return self


# ── Output ───────────────────────────────────────────────────────────────────

class MorphedQuestion(BaseModel):
    question: str
    options: list[str]
    correct_answer: str
    question_type: QuestionType
    morph_type: MorphStrategy
    difficulty_actual: DifficultyLevel
    semantic_score: float = Field(ge=0.0, le=1.0)
    answer_changed: bool = False
    quality_flags: list[str] = Field(default_factory=list)
    explanation: str = ""


class MorphOutput(BaseModel):
    trace_id: str
    original_question: str
    section: str
    variants: list[MorphedQuestion]
    morph_lineage: dict[str, str] = Field(default_factory=dict)
    total_variants: int = 0
    failed_variants: int = 0

    @model_validator(mode="after")
    def set_counts(self):
        self.total_variants = len(self.variants)
        return self