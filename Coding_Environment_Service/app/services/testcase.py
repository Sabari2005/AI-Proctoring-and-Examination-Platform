"""
testcase.py — Evaluates a submission against all test cases.
"""
import asyncio
import json
import re
import structlog
from typing import List

from app.config import settings
from app.schemas.schemas import TestCase, TestCaseResult, RunResult
from app.services.sandbox import sandbox_executor

log = structlog.get_logger()


def _normalize(s: str) -> str:
    """Normalize output for comparison: strip trailing whitespace per line, strip trailing newline."""
    lines = s.rstrip().splitlines()
    return "\n".join(line.rstrip() for line in lines)


def _build_python_function_source(source_code: str, tc: TestCase) -> str:
    args_json = json.dumps(tc.function_args or [])
    kwargs_json = json.dumps(tc.function_kwargs or {})
    match = re.search(r"def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", source_code)
    detected_function_name = match.group(1) if match else None
    function_name = tc.function_name or detected_function_name or "solve"
    harness = (
        "\n\n# --- Auto-generated function-mode harness ---\n"
        "import json\n"
        f"__tc_args = json.loads({args_json!r})\n"
        f"__tc_kwargs = json.loads({kwargs_json!r})\n"
        f"__result = {function_name}(*__tc_args, **__tc_kwargs)\n"
        "if __result is None:\n"
        "    print('None')\n"
        "elif isinstance(__result, (list, tuple)):\n"
        "    print(' '.join(str(x) for x in __result))\n"
        "elif isinstance(__result, str):\n"
        "    print(__result)\n"
        "else:\n"
        "    print(str(__result))\n"
    )
    return source_code + harness


def _prepare_execution_payload(language: str, source_code: str, tc: TestCase) -> tuple[str, str]:
    if language == "python":
        effective_tc = tc
        name_match = re.search(r"def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", source_code)
        inferred_name = name_match.group(1) if name_match else None

        if inferred_name and not tc.function_name and (tc.function_args is not None or tc.function_kwargs is not None):
            effective_tc = tc.model_copy(update={
                "function_name": inferred_name,
            })

        if tc.function_args is None and tc.function_kwargs is None:
            lines = [line.strip() for line in (tc.input or "").splitlines() if line.strip()]
            if inferred_name and len(lines) >= 3:
                try:
                    n = int(lines[0])
                    nums = [int(x) for x in lines[1].split()]
                    target = int(lines[2])
                    if n == len(nums):
                        effective_tc = tc.model_copy(update={
                            "function_name": tc.function_name or inferred_name,
                            "function_args": [nums, target],
                            "function_kwargs": {},
                        })
                except Exception:
                    pass

        if effective_tc.function_args is not None or effective_tc.function_kwargs is not None:
            return _build_python_function_source(source_code, effective_tc), ""

    return source_code, tc.input or ""


async def evaluate_submission(
    language: str,
    source_code: str,
    test_cases: List[TestCase],
    concurrency: int = 4,
) -> tuple[List[TestCaseResult], int, int]:
    """
    Run all test cases with bounded concurrency.
    Returns (results, passed_count, total_count).
    Early-terminates remaining cases after a compile error.
    """
    semaphore = asyncio.Semaphore(concurrency)
    results: List[TestCaseResult] = []
    compile_failed = False

    async def run_one(tc: TestCase) -> TestCaseResult:
        nonlocal compile_failed
        if compile_failed:
            return TestCaseResult(
                test_case_id=tc.id,
                passed=False,
                error="Skipped due to compilation error",
            )

        run_source, run_stdin = _prepare_execution_payload(language, source_code, tc)

        async with semaphore:
            run: RunResult = await sandbox_executor.run(
                language=language,
                source_code=run_source,
                stdin=run_stdin,
                time_limit_seconds=tc.time_limit_ms // 1000 if tc.time_limit_ms else settings.MAX_EXECUTION_TIME_SECONDS,
                memory_limit_mb=tc.memory_limit_mb or settings.MAX_MEMORY_MB,
            )

        # Compilation error check (non-zero on first compile)
        if run.exit_code == 1 and not run.stdout and run.stderr and language in ("java", "cpp", "go", "rust"):
            compile_failed = True

        if run.timed_out:
            return TestCaseResult(
                test_case_id=tc.id,
                passed=False,
                actual_output="",
                expected_output=tc.expected_output if tc.is_sample else None,
                execution_time_ms=run.execution_time_ms,
                memory_used_kb=run.memory_used_kb,
                error="Time limit exceeded",
            )

        if run.exit_code != 0:
            return TestCaseResult(
                test_case_id=tc.id,
                passed=False,
                actual_output=run.stdout,
                expected_output=tc.expected_output if tc.is_sample else None,
                execution_time_ms=run.execution_time_ms,
                memory_used_kb=run.memory_used_kb,
                error=run.stderr[:1024] if run.stderr else f"Runtime error (exit {run.exit_code})",
            )

        if tc.expected_output_json is not None:
            expected_json_text = json.dumps(tc.expected_output_json, separators=(",", ":"), ensure_ascii=False)
            expected_seq_text = " ".join(str(x) for x in tc.expected_output_json) if isinstance(tc.expected_output_json, (list, tuple)) else expected_json_text
            try:
                parsed = json.loads(run.stdout.strip() or "null")
                passed = parsed == tc.expected_output_json
                actual_for_sample = json.dumps(parsed, separators=(",", ":"), ensure_ascii=False)
            except Exception:
                normalized_actual = _normalize(run.stdout)
                passed = normalized_actual in {_normalize(expected_json_text), _normalize(expected_seq_text), _normalize(tc.expected_output)}
                actual_for_sample = run.stdout
            expected_for_sample = tc.expected_output if tc.expected_output else expected_seq_text
        else:
            passed = _normalize(run.stdout) == _normalize(tc.expected_output)
            actual_for_sample = run.stdout
            expected_for_sample = tc.expected_output

        return TestCaseResult(
            test_case_id=tc.id,
            passed=passed,
            actual_output=actual_for_sample if tc.is_sample else None,
            expected_output=expected_for_sample if tc.is_sample else None,
            execution_time_ms=run.execution_time_ms,
            memory_used_kb=run.memory_used_kb,
        )

    tasks = [run_one(tc) for tc in test_cases]
    results = await asyncio.gather(*tasks)

    passed = sum(1 for r in results if r.passed)
    log.info("evaluation_done", language=language, passed=passed, total=len(test_cases))
    return list(results), passed, len(test_cases)
