"""
app/core/qtype_state.py
────────────────────────
Unified LangGraph TypedDict state that works for all 5 question types.
The `input` field accepts any of the 5 input types — the graph dispatches
to the right node set based on qtype detected at runtime.
"""
from typing import Optional, Annotated, Union, Any
import operator
from typing_extensions import TypedDict

from .qtype_enums import QType
from .qtype_schemas import (
    FIBInput, ShortInput, MSQInput, NumericalInput, LongInput,
    MorphedFIB, MorphedShort, MorphedMSQ, MorphedNumerical, MorphedLong,
)
from .enums import DifficultyLevel, BloomLevel, ValidationStatus

# Union of all input types
AnyQInput = Union[FIBInput, ShortInput, MSQInput, NumericalInput, LongInput]

# Union of all morphed output types
AnyMorphedQ = Union[MorphedFIB, MorphedShort, MorphedMSQ, MorphedNumerical, MorphedLong]


class QTypeAnalysisResult(TypedDict):
    qtype: QType
    concept: str
    bloom_level: BloomLevel
    topic_tags: list[str]
    answer_structure: str       # "free_text" | "numeric" | "multi_select" | "rubric"
    key_terms: list[str]        # important terms extracted from question


class QTypeValidationReport(TypedDict):
    status: ValidationStatus
    semantic_score: float
    answer_valid: bool
    failure_reasons: list[str]


class QTypeMorphState(TypedDict):
    # ── Core ─────────────────────────────────────────────────
    input: AnyQInput
    qtype: QType
    trace_id: str
    difficulty_input_provided: Optional[bool]

    # ── Analysis ─────────────────────────────────────────────
    analysis_result: Optional[QTypeAnalysisResult]
    difficulty_target: Optional[DifficultyLevel]
    bloom_target: Optional[BloomLevel]

    # ── Morph (fan-in via operator.add) ──────────────────────
    morphed_variants: Annotated[list[AnyMorphedQ], operator.add]

    # ── Validation ───────────────────────────────────────────
    validation_report: Optional[QTypeValidationReport]
    retry_count: int
    current_strategy: Optional[str]

    # ── Output ───────────────────────────────────────────────
    final_output: Optional[dict]
    error: Optional[str]