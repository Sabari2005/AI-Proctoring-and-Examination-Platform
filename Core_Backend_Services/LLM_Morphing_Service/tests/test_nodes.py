"""
Unit tests — test each node in isolation (no graph wiring needed).
Run with:  pytest tests/test_nodes.py -v
"""
import pytest
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from app.core.schemas import MorphInput, MorphConfig
from app.core.enums import MorphStrategy, DifficultyLevel, QuestionType
from app.core.state import MorphState


# ── Fixture ──────────────────────────────────────────────────────────────────

def base_state(strategies: list[MorphStrategy] = None) -> MorphState:
    """Build a minimal valid MorphState for testing individual nodes."""
    strategies = strategies or [MorphStrategy.REPHRASE]
    inp = MorphInput(
        section="Aptitude",
        question="A train travels 60 km in 1 hour. How long to travel 210 km?",
        options=["2.5 hours", "3.5 hours", "4 hours", "3 hours", "5 hours"],
        correct_answer="3.5 hours",
        difficulty=DifficultyLevel.MEDIUM,
        morph_config=MorphConfig(strategies=strategies),
    )
    return {
        "input":             inp,
        "trace_id":          "test-trace",
        "analysis_result": {
            "concept":    "speed-time-distance",
            "formula":    "time = distance / speed",
            "key_values": {"speed": 60, "distance": 210},
            "bloom_level": "apply",
            "topic_tags": ["aptitude", "time-speed-distance"],
        },
        "difficulty_target": DifficultyLevel.MEDIUM,
        "bloom_target":      None,
        "morphed_variants":  [],
        "validation_report": None,
        "retry_count":       0,
        "current_strategy":  None,
        "final_output":      None,
        "error":             None,
    }


# ── Utility tests (no LLM calls) ─────────────────────────────────────────────

def test_json_parser_clean():
    from app.utils.json_parser import parse_llm_json
    raw = '{"question": "A cyclist rides at 60 km/h."}'
    result = parse_llm_json(raw)
    assert result["question"] == "A cyclist rides at 60 km/h."


def test_json_parser_with_fences():
    from app.utils.json_parser import parse_llm_json
    raw = '```json\n{"question": "A cyclist rides."}\n```'
    result = parse_llm_json(raw)
    assert "question" in result


def test_similarity_identical():
    from app.utils.similarity import compute_similarity
    score = compute_similarity("A train travels fast.", "A train travels fast.")
    assert score > 0.99


def test_similarity_different():
    from app.utils.similarity import compute_similarity
    score = compute_similarity("A train travels fast.", "The moon is made of cheese.")
    assert score < 0.5


def test_trace_id_format():
    from app.utils.trace import generate_trace_id
    tid = generate_trace_id()
    assert tid.startswith("mrph-")
    assert len(tid.split("-")) == 3


def test_input_validation_correct_answer_not_in_options():
    with pytest.raises(Exception):
        MorphInput(
            section="Aptitude",
            question="What is 2+2?",
            options=["3", "4", "5"],
            correct_answer="6",     # Not in options — should raise
        )


def test_calibrate_difficulty_no_llm():
    from app.nodes.calibrate import calibrate_difficulty
    state = base_state()
    result = calibrate_difficulty(state)
    assert "difficulty_target" in result
    assert "bloom_target" in result


# ── Node tests (require API keys + network) ───────────────────────────────────

@pytest.mark.integration
def test_analyze_question():
    from app.nodes.analyze import analyze_question
    state   = base_state()
    result  = analyze_question(state)
    assert "analysis_result" in result
    assert "trace_id" in result
    analysis = result["analysis_result"]
    assert "concept" in analysis
    assert "bloom_level" in analysis


@pytest.mark.integration
def test_morph_rephrase():
    from app.nodes.morph_rephrase import morph_rephrase
    state   = base_state([MorphStrategy.REPHRASE])
    result  = morph_rephrase(state)
    assert len(result["morphed_variants"]) == 1
    v = result["morphed_variants"][0]
    assert v.correct_answer == "3.5 hours"
    assert v.answer_changed is False
    assert v.semantic_score > 0.0


@pytest.mark.integration
def test_morph_distractor():
    from app.nodes.morph_distractor import morph_distractor
    state  = base_state([MorphStrategy.DISTRACTOR])
    result = morph_distractor(state)
    v = result["morphed_variants"][0]
    assert v.correct_answer in v.options
    assert len(v.options) >= 3


@pytest.mark.integration
def test_morph_difficulty():
    from app.nodes.morph_difficulty import morph_difficulty
    state = base_state([MorphStrategy.DIFFICULTY])
    state["difficulty_target"] = DifficultyLevel.HARD
    result = morph_difficulty(state)
    v = result["morphed_variants"][0]
    assert v.answer_changed is True
    assert v.correct_answer in v.options


@pytest.mark.integration
def test_full_graph_rephrase():
    """End-to-end test: run the full graph with a single rephrase strategy."""
    from app.graph.builder import morph_graph
    import asyncio

    state = base_state([MorphStrategy.REPHRASE])

    async def run():
        return await morph_graph.ainvoke(state)

    result = asyncio.run(run())
    assert result["final_output"] is not None
    output = result["final_output"]
    assert len(output["variants"]) >= 1
    assert output["variants"][0]["correct_answer"] == "3.5 hours"