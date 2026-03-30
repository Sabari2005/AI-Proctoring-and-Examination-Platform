"""
app/core/coding_state.py
─────────────────────────
LangGraph TypedDict state for the coding question morphing pipeline.
Drop this into app/core/ alongside the existing state.py.
"""
from typing import Optional, Annotated
import operator
from typing_extensions import TypedDict

from .coding_schemas import CodingMorphInput, MorphedCodingQuestion
from .enums import DifficultyLevel, BloomLevel, ValidationStatus


class CodingAnalysisResult(TypedDict):
    algorithm_category: str    # e.g. "two-pointer", "dynamic-programming", "hash-map"
    data_structures: list[str] # e.g. ["array", "hash-map"]
    time_complexity: str        # e.g. "O(n)"
    space_complexity: str       # e.g. "O(n)"
    bloom_level: BloomLevel
    topic_tags: list[str]
    core_logic: str             # one-sentence description of what the solution does


class CodingValidationReport(TypedDict):
    status: ValidationStatus
    semantic_score: float
    tc_count_valid: int          # how many TCs have correct format
    tc_count_total: int
    answer_correct: bool         # True if TCs were re-verified for difficulty morph
    failure_reasons: list[str]


class CodingMorphState(TypedDict):
    # ── Input ────────────────────────────────────────────────
    input: CodingMorphInput
    trace_id: str

    # ── Analysis ─────────────────────────────────────────────
    analysis_result: Optional[CodingAnalysisResult]
    difficulty_target: Optional[DifficultyLevel]
    bloom_target: Optional[BloomLevel]

    # ── Morph (fan-in via operator.add) ──────────────────────
    morphed_variants: Annotated[list[MorphedCodingQuestion], operator.add]

    # ── Validation ───────────────────────────────────────────
    validation_report: Optional[CodingValidationReport]
    retry_count: int
    current_strategy: Optional[str]

    # ── Output ───────────────────────────────────────────────
    final_output: Optional[dict]
    error: Optional[str]