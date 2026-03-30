"""
run.py
───────
Quick-start script to run the morphing pipeline directly from the terminal.
No FastAPI needed — invoke the graph straight from Python.

Usage:
    python run.py                          # uses built-in sample question
    python run.py --input-file tests/fixtures/sample_question.json
    python run.py --strategy rephrase
    python run.py --strategy distractor
    python run.py --strategy contextual
    python run.py --strategy structural
    python run.py --strategy difficulty
    python run.py --strategy rephrase distractor   # multiple strategies
    python run.py --input-file tests/fixtures/sample_question.json --strategy rephrase
"""
import asyncio
import argparse
import json
from dotenv import load_dotenv

load_dotenv()

from app.core.schemas import MorphInput, MorphConfig
from app.core.enums import MorphStrategy, DifficultyLevel
from app.core.state import MorphState
from app.graph.builder import morph_graph


# ── Sample question (your Aptitude example) ───────────────────────────────────
SAMPLE = {
    "section":        "Aptitude",
    "question":       "A train travels 60 km in 1 hour. How long will it take to travel 210 km at the same speed?",
    "options":        ["2.5 hours", "3.5 hours", "4 hours", "3 hours", "5 hours"],
    "correct_answer": "3.5 hours",
}


def _load_input_payload(input_file: str | None) -> dict:
    if not input_file:
        return {
            **SAMPLE,
            "difficulty": DifficultyLevel.MEDIUM.value,
            "morph_config": {
                "strategies": [MorphStrategy.REPHRASE.value],
                "variant_count": 1,
                "preserve_answer": True,
            },
        }

    with open(input_file, "r", encoding="utf-8") as f:
        return json.load(f)


async def run_morph(input_file: str | None, strategies: list[str] | None) -> dict:
    payload = _load_input_payload(input_file)
    inp = MorphInput(**payload)

    if strategies:
        strategy_enums = [MorphStrategy(s) for s in strategies]
        inp.morph_config = MorphConfig(
            strategies=strategy_enums,
            variant_count=len(strategy_enums),
            preserve_answer=inp.morph_config.preserve_answer,
            target_difficulty=inp.morph_config.target_difficulty,
            preserve_format=inp.morph_config.preserve_format,
        )

    initial_state: MorphState = {
        "input":             inp,
        "trace_id":          "",
        "analysis_result":   None,
        "difficulty_target": None,
        "bloom_target":      None,
        "morphed_variants":  [],
        "validation_report": None,
        "retry_count":       0,
        "current_strategy":  None,
        "final_output":      None,
        "error":             None,
    }

    print(f"\n{'='*60}")
    print(f"  LLM Question Morphing Pipeline")
    print(f"  Strategies: {[s.value for s in inp.morph_config.strategies]}")
    print(f"{'='*60}\n")

    result = await morph_graph.ainvoke(initial_state)
    return result.get("final_output", {})


def print_output(output: dict):
    print(f"\n{'='*60}")
    print(f"  OUTPUT  |  trace_id: {output.get('trace_id')}")
    print(f"{'='*60}")
    print(f"  Original : {output.get('original_question')}")
    print(f"  Section  : {output.get('section')}")
    print(f"  Variants : {output.get('total_variants')}\n")

    for i, v in enumerate(output.get("variants", []), 1):
        print(f"  ── Variant {i} [{v['morph_type'].upper()}] ──────────────────")
        print(f"  Question : {v['question']}")
        print(f"  Options  : {v['options']}")
        print(f"  Answer   : {v['correct_answer']}")
        print(f"  Difficulty: {v['difficulty_actual']}  |  Semantic: {v['semantic_score']}")
        if v.get("quality_flags"):
            print(f"  Flags    : {v['quality_flags']}")
        if v.get("explanation"):
            print(f"  Note     : {v['explanation']}")
        print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run LLM Question Morphing")
    parser.add_argument(
        "--input-file",
        default=None,
        help="Path to a JSON input payload (same shape as MorphInput)",
    )
    parser.add_argument(
        "--strategy",
        nargs="+",
        choices=[s.value for s in MorphStrategy],
        default=None,
        help="Optional strategy/strategies to override morph_config.strategies",
    )
    args = parser.parse_args()

    output = asyncio.run(run_morph(args.input_file, args.strategy))
    print_output(output)

    # Also save raw JSON output
    with open("last_output.json", "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"  Full output saved to last_output.json\n")