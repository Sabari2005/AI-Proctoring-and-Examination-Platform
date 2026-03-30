import json
from typing import Any

from app.core.coding_schemas import CodingMorphConfig, CodingMorphInput
from app.core.coding_schemas import CodingConstraints, TestCase
from app.core.enums import BloomLevel, DifficultyLevel, MorphStrategy, QuestionType
from app.core.qtype_schemas import (
    FIBInput,
    FIBMorphConfig,
    FIBMorphStrategy,
    GradingRubric,
    LongInput,
    LongMorphConfig,
    LongMorphStrategy,
    MSQInput,
    MSQMorphConfig,
    MSQMorphStrategy,
    NumericalInput,
    NumericalMorphConfig,
    NumericalMorphStrategy,
    Rubric,
    RubricPoint,
    ShortInput,
    ShortMorphConfig,
    ShortMorphStrategy,
    WordLimit,
)
from app.core.schemas import MorphConfig, MorphInput
from server.models import Question


QUESTION_TYPE_MAP = {
    # MCQ variants
    "mcq": "mcq",
    "multiple choice": "mcq",
    "multiple_choice": "mcq",
    # MSQ variants
    "msq": "msq",
    "multiple select": "msq",
    "multiple_select": "msq",
    # FIB variants
    "fib": "fib",
    "fill in the blanks": "fib",
    "fill_blank": "fib",
    "fill_in_the_blank": "fib",
    "fill-in-the-blank": "fib",
    "fillblank": "fib",
    # Numerical variants
    "numeric": "numerical",
    "numerical": "numerical",
    # Short answer variants
    "short": "short",
    "short answer": "short",
    "short_answer": "short",
    # Long answer variants
    "long": "long",
    "long answer": "long",
    "long_answer": "long",
    "essay": "long",
    # Coding variants
    "coding": "coding",
    "code": "coding",
}


def parse_payload(question: Question) -> dict[str, Any]:
    raw = getattr(question, "payload_json", None)
    if not raw:
        return {}
    try:
        parsed = json.loads(str(raw))
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def normalize_question_type(question: Question) -> str:
    raw_type = str(getattr(question, "question_type", "MCQ") or "MCQ").strip().lower()
    return QUESTION_TYPE_MAP.get(raw_type, "mcq")


def normalize_difficulty(value: Any) -> DifficultyLevel:
    try:
        level = int(value or 3)
    except (TypeError, ValueError):
        level = 3
    level = max(1, min(5, level))
    return DifficultyLevel(level)


def _morph_config_payload(payload: dict[str, Any]) -> dict[str, Any]:
    raw = payload.get("morph_config")
    return raw if isinstance(raw, dict) else {}


def _pick_variant_count(payload: dict[str, Any], default: int = 1) -> int:
    morph_cfg = _morph_config_payload(payload)
    raw = morph_cfg.get("variant_count", default)
    try:
        count = int(raw)
    except (TypeError, ValueError):
        count = default
    return max(1, min(5, count))


def _pick_source_difficulty(question: Question, payload: dict[str, Any]) -> DifficultyLevel:
    # Backward compatible: use payload difficulty if provided, otherwise DB taxonomy_level.
    return normalize_difficulty(payload.get("difficulty", getattr(question, "taxonomy_level", 3)))


def _pick_target_difficulty(payload: dict[str, Any]) -> DifficultyLevel | None:
    morph_cfg = _morph_config_payload(payload)
    raw = morph_cfg.get("target_difficulty")
    if raw is None or str(raw).strip() == "":
        return None
    return normalize_difficulty(raw)


def _pick_bloom_target(payload: dict[str, Any]) -> BloomLevel | None:
    morph_cfg = _morph_config_payload(payload)
    raw = morph_cfg.get("bloom_target")
    if raw is None:
        return None
    token = str(raw).strip().lower()
    if not token:
        return None
    try:
        return BloomLevel(token)
    except ValueError:
        return None


def _collect_options(question: Question, payload: dict[str, Any]) -> list[str]:
    payload_options = payload.get("options")
    if isinstance(payload_options, list):
        cleaned = [str(opt).strip() for opt in payload_options if str(opt).strip()]
        if cleaned:
            return cleaned

    options = [
        getattr(question, "option_a", None),
        getattr(question, "option_b", None),
        getattr(question, "option_c", None),
        getattr(question, "option_d", None),
    ]
    return [str(opt).strip() for opt in options if str(opt or "").strip()]


def _resolve_mcq_answer(raw_answer: Any, options: list[str]) -> str:
    if raw_answer is None:
        return ""

    if isinstance(raw_answer, list):
        raw_answer = raw_answer[0] if raw_answer else ""

    value = str(raw_answer).strip()
    if not value:
        return ""

    letter_to_index = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4, "F": 5}
    up = value.upper()
    if up in letter_to_index and letter_to_index[up] < len(options):
        return options[letter_to_index[up]]

    for option in options:
        if option.strip().lower() == value.lower():
            return option

    return value


def _base_question_text(question: Question, payload: dict[str, Any]) -> str:
    return (
        str(payload.get("question") or "").strip()
        or str(payload.get("question_test") or "").strip()
        or str(getattr(question, "question_text", "") or "").strip()
    )


def _generic_to_qtype_strategy(qtype: str, strategy: str) -> str:
    generic = strategy.strip().lower()
    if generic.startswith(f"{qtype}_"):
        generic = generic[len(qtype) + 1 :]
    mapping = {
        "fib": {
            "rephrase": FIBMorphStrategy.REPHRASE.value,
            "contextual": FIBMorphStrategy.CONTEXTUAL.value,
            "difficulty": FIBMorphStrategy.DIFFICULTY.value,
            "structural": FIBMorphStrategy.MULTBLANK.value,
        },
        "short": {
            "rephrase": ShortMorphStrategy.REPHRASE.value,
            "contextual": ShortMorphStrategy.CONTEXTUAL.value,
            "difficulty": ShortMorphStrategy.DIFFICULTY.value,
            "structural": ShortMorphStrategy.KEYWORD_SHIFT.value,
        },
        "msq": {
            "rephrase": MSQMorphStrategy.REPHRASE.value,
            "contextual": MSQMorphStrategy.CONTEXTUAL.value,
            "difficulty": MSQMorphStrategy.DIFFICULTY.value,
            "distractor": MSQMorphStrategy.DISTRACTOR.value,
            "structural": MSQMorphStrategy.DISTRACTOR.value,
        },
        "numerical": {
            "rephrase": NumericalMorphStrategy.REPHRASE.value,
            "contextual": NumericalMorphStrategy.CONTEXTUAL.value,
            "difficulty": NumericalMorphStrategy.DIFFICULTY.value,
            "structural": NumericalMorphStrategy.VALUES.value,
        },
        "long": {
            "rephrase": LongMorphStrategy.REPHRASE.value,
            "contextual": LongMorphStrategy.CONTEXTUAL.value,
            "difficulty": LongMorphStrategy.DIFFICULTY.value,
            "structural": LongMorphStrategy.FOCUS_SHIFT.value,
        },
    }

    default_by_type = {
        "fib": FIBMorphStrategy.REPHRASE.value,
        "short": ShortMorphStrategy.REPHRASE.value,
        "msq": MSQMorphStrategy.REPHRASE.value,
        "numerical": NumericalMorphStrategy.REPHRASE.value,
        "long": LongMorphStrategy.REPHRASE.value,
    }

    return mapping.get(qtype, {}).get(generic, default_by_type[qtype])


def _extract_strategy(question: Question, payload: dict[str, Any], default: str = "rephrase") -> str:
    morph_cfg = _morph_config_payload(payload)
    cfg_strategies = morph_cfg.get("strategies")
    if isinstance(cfg_strategies, list) and cfg_strategies:
        val = str(cfg_strategies[0] or "").strip().lower()
        if val:
            return val

    raw = str(getattr(question, "morphing_strategy", "") or "").strip().lower()
    return raw or default

def _smart_parse_tc_value(value: Any) -> Any:
    """
    Convert a string test-case value to its most natural Python type.

    Called on both input and output fields so the morphing pipeline
    receives proper types (int, list, dict) rather than raw strings.

    Rules:
    - Non-strings pass through unchanged (list, dict, int already correct)
    - JSON-parseable strings → parsed (handles lists, dicts, booleans, null)
    - Pure integer strings → int
    - Pure float strings → float
    - Everything else stays as str (e.g. "Greater than 5", "Even", "Low")
    """
    if not isinstance(value, str):
        return value

    stripped = value.strip()
    if not stripped:
        return value

    # JSON parse handles: [1,2,3], {"a":1}, true, false, null, "string"
    if stripped[0] in ('{', '[', '"') or stripped in ('true', 'false', 'null'):
        try:
            return json.loads(stripped)
        except (json.JSONDecodeError, ValueError):
            pass

    # Pure integer (handles negatives too)
    try:
        return int(stripped)
    except ValueError:
        pass

    # Float
    try:
        return float(stripped)
    except ValueError:
        pass

    # Leave as string — e.g. "Greater than 5", "Even", "Low", "Odd"
    return value

# def _normalize_coding_test_cases(raw_test_cases: Any) -> dict[str, TestCase]:
#     if isinstance(raw_test_cases, dict):
#         normalized: dict[str, TestCase] = {}
#         for name, tc in raw_test_cases.items():
#             if not isinstance(tc, dict):
#                 continue
#             if "input" not in tc or "output" not in tc:
#                 continue
#             key = str(name or "").strip() or f"tc_{len(normalized)+1}"
#             visibility = str(tc.get("visibility") or "").strip().lower()
#             normalized[key] = TestCase(
#                 input=tc.get("input"),
#                 output=tc.get("output"),
#                 is_hidden=bool(tc.get("is_hidden", visibility == "hidden")),
#                 category=str(tc.get("category") or "basic"),
#                 explanation=str(tc.get("explanation") or ""),
#             )
#         return normalized

#     if isinstance(raw_test_cases, list):
#         normalized = {}
#         for idx, tc in enumerate(raw_test_cases, start=1):
#             if not isinstance(tc, dict):
#                 continue
#             if "input" not in tc or "output" not in tc:
#                 continue
#             visibility = str(tc.get("visibility") or "").strip().lower()
#             normalized[f"tc_{idx}"] = TestCase(
#                 input=tc.get("input"),
#                 output=tc.get("output"),
#                 is_hidden=visibility == "hidden",
#                 category=str(tc.get("category") or ("hidden" if visibility == "hidden" else "basic")),
#                 explanation=str(tc.get("explanation") or ""),
#             )
#         return normalized

#     return {}

def _normalize_coding_test_cases(raw_test_cases: Any) -> dict[str, TestCase]:
    if isinstance(raw_test_cases, dict):
        normalized: dict[str, TestCase] = {}
        for name, tc in raw_test_cases.items():
            if not isinstance(tc, dict):
                continue
            if "input" not in tc or "output" not in tc:
                continue
            key = str(name or "").strip() or f"tc_{len(normalized)+1}"
            visibility = str(tc.get("visibility") or "").strip().lower()
            normalized[key] = TestCase(
                input=_smart_parse_tc_value(tc.get("input")),
                output=_smart_parse_tc_value(tc.get("output")),
                is_hidden=bool(tc.get("is_hidden", visibility == "hidden")),
                category=str(tc.get("category") or "basic"),
                explanation=str(tc.get("explanation") or ""),
            )
        return normalized

    if isinstance(raw_test_cases, list):
        normalized = {}
        for idx, tc in enumerate(raw_test_cases, start=1):
            if not isinstance(tc, dict):
                continue
            if "input" not in tc or "output" not in tc:
                continue
            visibility = str(tc.get("visibility") or "").strip().lower()
            normalized[f"tc_{idx}"] = TestCase(
                input=_smart_parse_tc_value(tc.get("input")),
                output=_smart_parse_tc_value(tc.get("output")),
                is_hidden=visibility == "hidden",
                category=str(tc.get("category") or ("hidden" if visibility == "hidden" else "basic")),
                explanation=str(tc.get("explanation") or ""),
            )
        return normalized

    return {}


def build_input_from_question(question: Question) -> tuple[str, Any] | tuple[None, None]:
    payload = parse_payload(question)
    qtype = normalize_question_type(question)
    text = _base_question_text(question, payload)
    difficulty = _pick_source_difficulty(question, payload)
    target_difficulty = _pick_target_difficulty(payload)
    bloom_target = _pick_bloom_target(payload)
    variant_count = _pick_variant_count(payload, default=1)
    strategy = _extract_strategy(question, payload, default="rephrase")

    if not text:
        return None, None

    if qtype == "mcq":
        options = _collect_options(question, payload)
        if len(options) < 2:
            return None, None

        raw_answer = payload.get("correct_answer", getattr(question, "correct_option", None))
        correct_answer = _resolve_mcq_answer(raw_answer, options)
        if not correct_answer:
            return None, None

        if correct_answer not in options:
            options = [*options, correct_answer]

        strategy_value = strategy if strategy in {s.value for s in MorphStrategy} else MorphStrategy.REPHRASE.value

        model = MorphInput(
            section=str(payload.get("section") or "General"),
            question=text,
            options=options,
            correct_answer=correct_answer,
            question_type=QuestionType.MCQ,
            difficulty=difficulty,
            morph_config=MorphConfig(
                strategies=[MorphStrategy(strategy_value)],
                variant_count=variant_count,
                preserve_answer=True,
                target_difficulty=target_difficulty,
            ),
        )
        return qtype, model

    if qtype == "fib":
        answers = payload.get("correct_answers")
        if not isinstance(answers, list):
            single = payload.get("correct_answer", getattr(question, "correct_option", None))
            answers = [str(single).strip()] if str(single or "").strip() else []

        if not answers:
            return None, None

        fib_text = text
        if "________" not in fib_text and "____" not in fib_text:
            # Some DB rows are tagged as FIB but store plain question text without
            # the required blank marker. Normalize instead of skipping the question.
            fib_text = f"{fib_text.rstrip(' ?.')}: ________"

        model = FIBInput(
            section=str(payload.get("section") or "General"),
            question=fib_text,
            blank_positions=payload.get("blank_positions") or [],
            correct_answers=[str(v).strip() for v in answers if str(v).strip()],
            difficulty=difficulty,
            morph_config=FIBMorphConfig(
                strategies=[FIBMorphStrategy(_generic_to_qtype_strategy("fib", strategy))],
                variant_count=variant_count,
                target_difficulty=target_difficulty,
                bloom_target=bloom_target,
            ),
        )
        return qtype, model

    if qtype == "short":
        model_answer = str(payload.get("model_answer") or payload.get("correct_answer") or "").strip()
        if len(model_answer) < 5:
            return None, None

        model = ShortInput(
            section=str(payload.get("section") or "General"),
            question=text,
            model_answer=model_answer,
            keywords=[str(v).strip() for v in payload.get("keywords", []) if str(v).strip()],
            min_words=int(payload.get("min_words", 10) or 10),
            max_words=int(payload.get("max_words", 100) or 100),
            grading_rubric=GradingRubric(**(payload.get("grading_rubric") or {})),
            difficulty=difficulty,
            morph_config=ShortMorphConfig(
                strategies=[ShortMorphStrategy(_generic_to_qtype_strategy("short", strategy))],
                variant_count=variant_count,
                target_difficulty=target_difficulty,
                bloom_target=bloom_target,
            ),
        )
        return qtype, model

    if qtype == "msq":
        options = _collect_options(question, payload)
        raw_correct = payload.get("correct_answers")
        if not isinstance(raw_correct, list):
            raw_correct = payload.get("correct_answer", [])
            raw_correct = raw_correct if isinstance(raw_correct, list) else [raw_correct]

        correct_answers = []
        for value in raw_correct:
            resolved = _resolve_mcq_answer(value, options)
            if resolved and resolved not in correct_answers:
                correct_answers.append(resolved)

        if len(options) < 4 or len(correct_answers) < 2:
            return None, None

        model = MSQInput(
            section=str(payload.get("section") or "General"),
            question=text,
            options=options,
            correct_answers=correct_answers,
            partial_credit=bool(payload.get("partial_credit", True)),
            penalty_for_wrong=bool(payload.get("penalty_for_wrong", False)),
            difficulty=difficulty,
            morph_config=MSQMorphConfig(
                strategies=[MSQMorphStrategy(_generic_to_qtype_strategy("msq", strategy))],
                variant_count=variant_count,
                target_difficulty=target_difficulty,
                bloom_target=bloom_target,
            ),
        )
        return qtype, model

    if qtype == "numerical":
        raw_value = payload.get("correct_value", payload.get("correct_answer"))
        if raw_value is None:
            return None, None

        try:
            correct_value = float(raw_value)
        except (TypeError, ValueError):
            return None, None

        model = NumericalInput(
            section=str(payload.get("section") or "General"),
            question=text,
            correct_value=correct_value,
            unit=str(payload.get("unit") or ""),
            tolerance=float(payload.get("tolerance", 0.0) or 0.0),
            decimal_places=int(payload.get("decimal_places", 2) or 2),
            formula=str(payload.get("formula") or ""),
            difficulty=difficulty,
            morph_config=NumericalMorphConfig(
                strategies=[NumericalMorphStrategy(_generic_to_qtype_strategy("numerical", strategy))],
                variant_count=variant_count,
                target_difficulty=target_difficulty,
                bloom_target=bloom_target,
            ),
        )
        return qtype, model

    if qtype == "long":
        rubric_data = payload.get("rubric") or {}
        points = rubric_data.get("points") or []

        if not points:
            # No rubric stored — auto-generate one from the plain correct_answer
            # text. This handles the common DB format where vendors store a
            # plain-text model answer instead of a structured rubric.
            raw_answer_text = str(
                payload.get("correct_answer")
                or payload.get("model_answer")
                or getattr(question, "correct_option", "")
                or ""
            ).strip()

            if not raw_answer_text:
                return None, None

            # Store model_answer in payload so the LLM prompts receive it
            # as topic context even though no rubric existed originally.
            payload["model_answer"] = raw_answer_text

            # Split answer into sentences/lines to create rubric points.
            # Each non-empty line or sentence becomes one rubric point.
            import re as _re
            # Split on newlines first, then on sentence boundaries for single-line answers
            raw_lines = [l.strip() for l in raw_answer_text.splitlines() if l.strip()]
            if len(raw_lines) <= 1:
                # Single line answer — split on sentence boundaries
                raw_lines = [
                    s.strip() for s in _re.split(r"(?<=[.!?])\s+", raw_answer_text)
                    if s.strip()
                ]
            if not raw_lines:
                raw_lines = [raw_answer_text]

            # Cap at 5 rubric points, distribute marks evenly
            raw_lines = raw_lines[:5]
            marks_per_point = max(1, round(100 / len(raw_lines)))
            # Adjust last point to make total exactly 100
            marks_list = [marks_per_point] * len(raw_lines)
            marks_list[-1] = 100 - marks_per_point * (len(raw_lines) - 1)

            # Extract keywords from each line (words > 3 chars, not stop words)
            _STOP = {
                "the", "a", "an", "is", "are", "was", "were", "in", "of",
                "to", "and", "or", "it", "its", "for", "on", "at", "by",
                "this", "that", "with", "from", "has", "have", "be", "been",
                "such", "as", "can", "used", "also", "these", "which",
            }

            def _extract_keywords(line: str) -> list[str]:
                return [
                    w.strip(".,;:!?\"'()→–-")
                    for w in line.split()
                    if len(w) > 3
                    and w.lower().strip(".,;:!?\"'()→–-") not in _STOP
                ][:4]

            points = [
                {
                    "point": line,
                    "marks": marks_list[i],
                    "keywords": _extract_keywords(line),
                }
                for i, line in enumerate(raw_lines)
            ]

        # Build rubric points defensively — skip malformed points
        rubric_points: list[RubricPoint] = []
        for raw_point in points:
            if not isinstance(raw_point, dict):
                continue
            point_text = str(
                raw_point.get("point")
                or raw_point.get("criterion")
                or raw_point.get("description")
                or ""
            ).strip()
            if not point_text:
                continue
            try:
                marks_val = int(
                    raw_point.get("marks")
                    or raw_point.get("score")
                    or raw_point.get("weight")
                    or 0
                )
            except (TypeError, ValueError):
                marks_val = 0
            raw_kws = raw_point.get("keywords") or []
            rubric_points.append(RubricPoint(
                point=point_text,
                marks=marks_val,
                keywords=[str(k).strip() for k in raw_kws if str(k).strip()]
                         if isinstance(raw_kws, list) else [],
            ))

        if not rubric_points:
            return None, None

        rubric = Rubric(
            points=rubric_points,
            total_marks=int(rubric_data.get("total_marks", sum(p.marks for p in rubric_points))),
            min_areas=int(rubric_data.get("min_areas", 1)),
        )

        word_limit_data = payload.get("word_limit") or {}
        word_limit = WordLimit(
            min=int(word_limit_data.get("min", 100)),
            max=int(word_limit_data.get("max", 800)),
        )

        model = LongInput(
            section=str(payload.get("section") or "General"),
            question=text,
            rubric=rubric,
            word_limit=word_limit,
            requires_examples=bool(payload.get("requires_examples", False)),
            requires_diagrams=bool(payload.get("requires_diagrams", False)),
            difficulty=difficulty,
            morph_config=LongMorphConfig(
                strategies=[LongMorphStrategy(_generic_to_qtype_strategy("long", strategy))],
                variant_count=variant_count,
                target_difficulty=target_difficulty,
                bloom_target=bloom_target,
            ),
        )
        return qtype, model

    if qtype == "coding":
        test_cases = _normalize_coding_test_cases(payload.get("test_cases"))
        if len(test_cases) < 2:
            return None, None

        coding_strategy = strategy if strategy.startswith("code_") else "code_rephrase"
        constraints_payload = payload.get("constraints") if isinstance(payload.get("constraints"), dict) else {}
        morph_cfg = _morph_config_payload(payload)

        model = CodingMorphInput(
            section=str(payload.get("section") or "Coding"),
            question=text,
            test_cases=test_cases,
            constraints=CodingConstraints(
                time_complexity=(
                    constraints_payload.get("time_complexity")
                    or payload.get("time_complexity")
                    or getattr(question, "time_complexity", None)
                ),
                space_complexity=(
                    constraints_payload.get("space_complexity")
                    or payload.get("space_complexity")
                    or getattr(question, "space_complexity", None)
                ),
                forbidden_builtins=(
                    constraints_payload.get("forbidden_builtins")
                    or payload.get("forbidden_builtins")
                    or []
                ),
                notes=(
                    constraints_payload.get("notes")
                    or payload.get("notes")
                    or []
                ),
            ),
            difficulty=difficulty,
            topic_tags=payload.get("topic_tags") or payload.get("keyword_tags") or [],
            function_signature=str(payload.get("function_signature") or ""),
            morph_config=CodingMorphConfig(
                strategies=[coding_strategy],
                variant_count=variant_count,
                target_difficulty=target_difficulty,
                tc_count=int(morph_cfg.get("tc_count", payload.get("tc_count", 6)) or 6),
                add_edge_cases=bool(morph_cfg.get("add_edge_cases", payload.get("add_edge_cases", True))),
                add_stress_tests=bool(morph_cfg.get("add_stress_tests", payload.get("add_stress_tests", False))),
                target_language=str(morph_cfg.get("target_language") or payload.get("target_language") or "python"),
            ),
        )
        return qtype, model

    return None, None
