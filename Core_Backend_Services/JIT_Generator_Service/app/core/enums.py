from enum import Enum


class QType(str, Enum):
    MCQ       = "mcq"
    FIB       = "fib"
    SHORT     = "short"
    MSQ       = "msq"
    NUMERICAL = "numerical"
    LONG      = "long"
    CODING    = "coding"
    MIXED     = "mixed"          # rotate through all types


class DifficultyLevel(int, Enum):
    VERY_EASY = 1
    EASY      = 2
    MEDIUM    = 3
    HARD      = 4
    VERY_HARD = 5


class BloomLevel(str, Enum):
    REMEMBER  = "remember"
    UNDERSTAND = "understand"
    APPLY     = "apply"
    ANALYZE   = "analyze"
    EVALUATE  = "evaluate"


class SkillLabel(str, Enum):
    BEGINNER     = "Beginner"
    ELEMENTARY   = "Elementary"
    INTERMEDIATE = "Intermediate"
    ADVANCED     = "Advanced"
    EXPERT       = "Expert"


class AnswerStatus(str, Enum):
    CORRECT  = "correct"
    PARTIAL  = "partial"
    WRONG    = "wrong"
    SKIPPED  = "skipped"
    TIMEOUT  = "timeout"


DIFFICULTY_TO_BLOOM = {
    DifficultyLevel.VERY_EASY: BloomLevel.REMEMBER,
    DifficultyLevel.EASY:      BloomLevel.UNDERSTAND,
    DifficultyLevel.MEDIUM:    BloomLevel.APPLY,
    DifficultyLevel.HARD:      BloomLevel.ANALYZE,
    DifficultyLevel.VERY_HARD: BloomLevel.EVALUATE,
}

THETA_TO_SKILL = {
    (1.0, 1.8): SkillLabel.BEGINNER,
    (1.8, 2.6): SkillLabel.ELEMENTARY,
    (2.6, 3.4): SkillLabel.INTERMEDIATE,
    (3.4, 4.2): SkillLabel.ADVANCED,
    (4.2, 5.0): SkillLabel.EXPERT,
}


def theta_to_skill(theta: float) -> SkillLabel:
    for (lo, hi), label in THETA_TO_SKILL.items():
        if lo <= theta < hi:
            return label
    return SkillLabel.EXPERT if theta >= 4.2 else SkillLabel.BEGINNER