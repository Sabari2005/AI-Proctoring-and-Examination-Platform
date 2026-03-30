from typing import Optional, Any
from typing_extensions import TypedDict, Annotated
import operator

from .schemas import MorphInput, MorphedQuestion, MorphConfig
from .enums import DifficultyLevel, BloomLevel, ValidationStatus


class AnalysisResult(TypedDict):
    concept: str           # e.g. "speed-time-distance"
    formula: str           # e.g. "time = distance / speed"
    key_values: dict       # e.g. {"speed": 60, "distance": 210}
    bloom_level: BloomLevel
    topic_tags: list[str]


class ValidationReport(TypedDict):
    status: ValidationStatus
    semantic_score: float
    difficulty_drift: int
    answer_correct: bool
    is_duplicate: bool
    failure_reasons: list[str]


class MorphState(TypedDict):
    # ── Core input ──────────────────────────────────────
    input: MorphInput
    trace_id: str

    # ── Analysis phase ──────────────────────────────────
    analysis_result: Optional[AnalysisResult]
    difficulty_target: Optional[DifficultyLevel]
    bloom_target: Optional[BloomLevel]

    # ── Morph phase ─────────────────────────────────────
    # Annotated with operator.add so parallel nodes append instead of overwrite
    morphed_variants: Annotated[list[MorphedQuestion], operator.add]

    # ── Validation phase ─────────────────────────────────
    validation_report: Optional[ValidationReport]
    retry_count: int
    current_strategy: Optional[str]

    # ── Output phase ─────────────────────────────────────
    final_output: Optional[dict]
    error: Optional[str]