from enum import Enum


class MorphStrategy(str, Enum):
    REPHRASE = "rephrase"
    CONTEXTUAL = "contextual"
    DISTRACTOR = "distractor"
    STRUCTURAL = "structural"
    DIFFICULTY = "difficulty"


class QuestionType(str, Enum):
    MCQ = "mcq"
    FILL_BLANK = "fill_blank"
    TRUE_FALSE = "true_false"
    SHORT_ANSWER = "short_answer"


class DifficultyLevel(int, Enum):
    VERY_EASY = 1
    EASY = 2
    MEDIUM = 3
    HARD = 4
    VERY_HARD = 5


class BloomLevel(str, Enum):
    REMEMBER = "remember"
    UNDERSTAND = "understand"
    APPLY = "apply"
    ANALYZE = "analyze"
    EVALUATE = "evaluate"


class ValidationStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    RETRY = "retry"