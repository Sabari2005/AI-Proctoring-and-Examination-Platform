"""
app/core/coding_schemas.py
───────────────────────────
Pydantic models specific to coding question morphing.
These extend the existing schemas.py — drop this file into app/core/.

Key difference from MCQ:
  - No options / correct_answer field
  - Has test_cases: dict of {name: TestCase}
  - Has constraints: time/space complexity limits
  - Has language: target programming language
"""
from typing import Optional, Any
from pydantic import BaseModel, Field, model_validator
from .enums import DifficultyLevel


# ── Test Case ────────────────────────────────────────────────────────────────

class TestCase(BaseModel):
    input: Any          # Can be dict, list, int, str — anything
    output: Any         # Expected output — any type
    is_hidden: bool = False           # Hidden from candidate view
    explanation: str = ""             # Optional human-readable note
    category: str = "basic"          # basic | edge_case | stress | boundary


# ── Coding Constraints ───────────────────────────────────────────────────────

class CodingConstraints(BaseModel):
    time_complexity: Optional[str] = None    # e.g. "O(n)", "O(n log n)"
    space_complexity: Optional[str] = None  # e.g. "O(1)", "O(n)"
    forbidden_builtins: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)  # e.g. ["array is sorted"]


# ── Coding Morph Config ───────────────────────────────────────────────────────

class CodingMorphConfig(BaseModel):
    strategies: list[str] = Field(
        default=["code_rephrase"],
        description=(
            "code_rephrase | code_contextual | code_difficulty | "
            "code_constraint | code_tcgen | code_tcscale"
        )
    )
    variant_count: int = Field(default=1, ge=1, le=5)
    target_difficulty: Optional[DifficultyLevel] = None
    tc_count: int = Field(default=4, ge=2, le=20, description="Test cases per variant")
    add_edge_cases: bool = True
    add_stress_tests: bool = False
    target_language: str = "python"


# ── Main Coding Input ─────────────────────────────────────────────────────────

class CodingMorphInput(BaseModel):
    section: str = "Coding"
    question: str = Field(..., min_length=20)
    test_cases: dict[str, TestCase] = Field(
        ...,
        description="Dict of test case name → TestCase. Min 2 required."
    )
    constraints: CodingConstraints = Field(default_factory=CodingConstraints)
    difficulty: DifficultyLevel = Field(default=DifficultyLevel.MEDIUM)
    topic_tags: list[str] = Field(default_factory=list)  # e.g. ["array","hash-map"]
    function_signature: str = ""   # e.g. "def twoSum(nums, target):"
    morph_config: CodingMorphConfig = Field(default_factory=CodingMorphConfig)

    @model_validator(mode="after")
    def at_least_two_test_cases(self):
        if len(self.test_cases) < 2:
            raise ValueError("At least 2 test cases required for coding questions.")
        return self


# ── Morphed Coding Question ───────────────────────────────────────────────────

class MorphedCodingQuestion(BaseModel):
    question: str
    test_cases: dict[str, TestCase]
    constraints: CodingConstraints
    function_signature: str
    morph_type: str
    difficulty_actual: DifficultyLevel
    semantic_score: float = Field(ge=0.0, le=1.0)
    answer_changed: bool = False         # True only for difficulty morph
    tc_count_original: int = 0
    tc_count_morphed: int = 0
    quality_flags: list[str] = Field(default_factory=list)
    explanation: str = ""

    @model_validator(mode="after")
    def set_counts(self):
        self.tc_count_morphed = len(self.test_cases)
        return self


# ── Coding Output ─────────────────────────────────────────────────────────────

class CodingMorphOutput(BaseModel):
    trace_id: str
    original_question: str
    section: str
    variants: list[MorphedCodingQuestion]
    morph_lineage: dict[str, str] = Field(default_factory=dict)
    total_variants: int = 0
    failed_variants: int = 0

    @model_validator(mode="after")
    def set_total(self):
        self.total_variants = len(self.variants)
        return self