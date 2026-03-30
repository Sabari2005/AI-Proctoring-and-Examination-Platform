"""
app/core/qtype_enums.py
────────────────────────
Enums covering all question types and their morph strategies.
Add to app/core/ — extends the existing enums.py.
"""
from enum import Enum


class QType(str, Enum):
    MCQ         = "mcq"
    FIB         = "fib"           # Fill in the blank
    SHORT       = "short"         # Short answer
    MSQ         = "msq"           # Multiple select question
    NUMERICAL   = "numerical"
    LONG        = "long"          # Long answer / essay
    CODING      = "coding"


class AnswerTolerance(str, Enum):
    EXACT             = "exact"
    CASE_INSENSITIVE  = "case_insensitive"
    NUMERIC           = "numeric"           # for FIB with number answers
    SYNONYM           = "synonym"           # accept synonyms


class ToleranceType(str, Enum):
    ABSOLUTE   = "absolute"    # ±N units
    PERCENTAGE = "percentage"  # ±N%
    EXACT      = "exact"       # must match exactly


# ── Per-type morph strategy enums ────────────────────────────────────────────

class FIBMorphStrategy(str, Enum):
    REPHRASE    = "fib_rephrase"
    CONTEXTUAL  = "fib_contextual"
    DIFFICULTY  = "fib_difficulty"
    DISTRACTOR  = "fib_distractor"
    MULTBLANK   = "fib_multblank"
    CLOZIFY     = "fib_clozify"


class ShortMorphStrategy(str, Enum):
    REPHRASE      = "short_rephrase"
    CONTEXTUAL    = "short_contextual"
    DIFFICULTY    = "short_difficulty"
    KEYWORD_SHIFT = "short_keyword_shift"
    TO_MCQ        = "short_to_mcq"
    TO_LONG       = "short_to_long"


class MSQMorphStrategy(str, Enum):
    REPHRASE      = "msq_rephrase"
    DISTRACTOR    = "msq_distractor"
    DIFFICULTY    = "msq_difficulty"
    CONTEXTUAL    = "msq_contextual"
    PARTIAL_RULES = "msq_partial_rules"
    TO_MCQ        = "msq_to_mcq"


class NumericalMorphStrategy(str, Enum):
    REPHRASE    = "numerical_rephrase"
    CONTEXTUAL  = "numerical_contextual"
    VALUES      = "numerical_values"
    UNITS       = "numerical_units"
    DIFFICULTY  = "numerical_difficulty"
    TOLERANCE   = "numerical_tolerance"


class LongMorphStrategy(str, Enum):
    REPHRASE     = "long_rephrase"
    CONTEXTUAL   = "long_contextual"
    DIFFICULTY   = "long_difficulty"
    FOCUS_SHIFT  = "long_focus_shift"
    WORD_LIMIT   = "long_word_limit"
    TO_SHORT     = "long_to_short"