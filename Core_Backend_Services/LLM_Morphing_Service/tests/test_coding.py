"""
tests/test_coding.py
─────────────────────
Unit and integration tests for the coding question morphing pipeline.

Run unit tests (no API):
    pytest tests/test_coding.py -v -m "not integration"

Run all including LLM calls:
    pytest tests/test_coding.py -v
"""
import pytest
from dotenv import load_dotenv

load_dotenv()

from app.core.coding_schemas import (
    CodingMorphInput, CodingMorphConfig,
    CodingConstraints, TestCase,
)
from app.core.enums import DifficultyLevel
from app.core.coding_state import CodingMorphState


# ── Shared fixture ────────────────────────────────────────────────────────────

def make_state(strategies: list[str] = None) -> CodingMorphState:
    strategies = strategies or ["code_rephrase"]
    inp = CodingMorphInput(
        section="Coding",
        question=(
            "Given an array of integers nums and an integer target, "
            "return the indices of the two numbers that add up to target. "
            "Each input has exactly one solution."
        ),
        test_cases={
            "tc_1": TestCase(input={"nums": [2, 7, 11, 15], "target": 9},  output=[0, 1]),
            "tc_2": TestCase(input={"nums": [3, 2, 4],       "target": 6},  output=[1, 2]),
            "tc_3": TestCase(input={"nums": [3, 3],           "target": 6},  output=[0, 1]),
            "tc_4": TestCase(input={"nums": [-1,-2,-3,-4,-5],"target": -8}, output=[2, 4]),
        },
        constraints=CodingConstraints(),
        difficulty=DifficultyLevel.EASY,
        topic_tags=["array", "hash-map"],
        function_signature="def twoSum(nums: list[int], target: int) -> list[int]:",
        morph_config=CodingMorphConfig(
            strategies=strategies,
            tc_count=6,
            target_difficulty=DifficultyLevel.HARD if "code_difficulty" in strategies else None,
        ),
    )
    return {
        "input":             inp,
        "trace_id":          "test-001",
        "analysis_result": {
            "algorithm_category": "hash-map",
            "data_structures":    ["array", "hash-map"],
            "time_complexity":    "O(n)",
            "space_complexity":   "O(n)",
            "bloom_level":        "apply",
            "topic_tags":         ["array", "hash-map"],
            "core_logic":         "Use a hash map to store seen values and find complement.",
        },
        "difficulty_target": DifficultyLevel.EASY,
        "bloom_target":      None,
        "morphed_variants":  [],
        "validation_report": None,
        "retry_count":       0,
        "current_strategy":  None,
        "final_output":      None,
        "error":             None,
    }


# ── Unit tests (no LLM calls) ─────────────────────────────────────────────────

def test_coding_input_requires_two_test_cases():
    with pytest.raises(Exception):
        CodingMorphInput(
            section="Coding",
            question="Some question that is long enough to be valid",
            test_cases={
                "tc_1": TestCase(input={"nums": [1, 2]}, output=[0, 1])
                # Only 1 TC — should raise validation error
            },
        )


def test_coding_input_valid():
    state = make_state()
    assert state["input"].section == "Coding"
    assert len(state["input"].test_cases) == 4
    assert state["input"].function_signature.startswith("def twoSum")


def test_coding_calibrate_no_llm():
    from app.nodes.coding_calibrate import coding_calibrate_difficulty
    state  = make_state()
    result = coding_calibrate_difficulty(state)
    assert "difficulty_target" in result
    assert "bloom_target" in result


def test_tc_structure():
    """Every TC must have both input and output."""
    state = make_state()
    for name, tc in state["input"].test_cases.items():
        assert tc.input  is not None, f"{name} missing input"
        assert tc.output is not None, f"{name} missing output"


def test_coding_schemas_serialize():
    """MorphedCodingQuestion must serialize to dict cleanly."""
    from app.core.coding_schemas import MorphedCodingQuestion, CodingConstraints
    v = MorphedCodingQuestion(
        question="Test question",
        test_cases={"tc_1": TestCase(input={"nums": [1,2]}, output=[0,1])},
        constraints=CodingConstraints(),
        function_signature="def foo(): pass",
        morph_type="code_rephrase",
        difficulty_actual=DifficultyLevel.EASY,
        semantic_score=0.92,
    )
    d = v.model_dump()
    assert d["morph_type"] == "code_rephrase"
    assert d["tc_count_morphed"] == 1


# ── Integration tests (require API keys + network) ────────────────────────────

@pytest.mark.integration
def test_coding_analyze():
    from app.nodes.coding_analyze import coding_analyze_question
    state  = make_state()
    result = coding_analyze_question(state)
    assert "analysis_result" in result
    assert "trace_id" in result
    a = result["analysis_result"]
    assert "algorithm_category" in a
    assert "time_complexity" in a


@pytest.mark.integration
def test_morph_code_rephrase():
    from app.nodes.morph_code_rephrase import morph_code_rephrase
    state  = make_state(["code_rephrase"])
    result = morph_code_rephrase(state)
    v = result["morphed_variants"][0]
    assert v.answer_changed is False
    assert len(v.test_cases) == 4        # all original TCs preserved
    assert v.semantic_score > 0.0


@pytest.mark.integration
def test_morph_code_tcgen():
    from app.nodes.morph_code_tcgen import morph_code_tcgen
    state  = make_state(["code_tcgen"])
    result = morph_code_tcgen(state)
    v = result["morphed_variants"][0]
    assert v.answer_changed is False
    assert v.tc_count_morphed >= v.tc_count_original   # new TCs added


@pytest.mark.integration
def test_morph_code_difficulty():
    from app.nodes.morph_code_difficulty import morph_code_difficulty
    state = make_state(["code_difficulty"])
    state["difficulty_target"] = DifficultyLevel.HARD
    result = morph_code_difficulty(state)
    v = result["morphed_variants"][0]
    assert v.answer_changed is True
    assert len(v.test_cases) >= 1


@pytest.mark.integration
def test_full_coding_graph():
    """End-to-end: run full coding graph with rephrase + tcgen."""
    from app.graph.coding_builder import coding_morph_graph
    import asyncio

    state = make_state(["code_rephrase", "code_tcgen"])

    async def run():
        return await coding_morph_graph.ainvoke(state)

    result = asyncio.run(run())
    assert result["final_output"] is not None
    output = result["final_output"]
    assert output["total_variants"] >= 1
    print(f"\nFull graph output: {output['total_variants']} variants, "
          f"trace_id={output['trace_id']}")