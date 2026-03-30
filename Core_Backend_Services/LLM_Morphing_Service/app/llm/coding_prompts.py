"""
app/llm/coding_prompts.py
──────────────────────────
All ChatPromptTemplates for the 6 coding morph strategies.
Drop into app/llm/ alongside existing prompts.py.
"""
from langchain_core.prompts import ChatPromptTemplate


# ── Analyzer ─────────────────────────────────────────────────────────────────

CODING_ANALYZE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert competitive programming problem analyst.
Analyze the coding question and return a JSON object with these EXACT keys:
- algorithm_category : primary algorithm needed (e.g. "hash-map", "two-pointer", "dynamic-programming", "binary-search", "bfs", "dfs", "greedy", "sorting")
- data_structures    : list of data structures used (e.g. ["array", "hash-map"])
- time_complexity    : best achievable time complexity (e.g. "O(n)", "O(n log n)")
- space_complexity   : best achievable space complexity (e.g. "O(1)", "O(n)")
- bloom_level        : one of [remember, understand, apply, analyze, evaluate]
- topic_tags         : list of 3-5 relevant topic strings
- core_logic         : one sentence describing what the solution actually does

Return ONLY valid JSON. No explanation, no markdown fences."""),
    ("human", """Section: {section}
Question: {question}
Test Cases: {test_cases}
Existing Constraints: {constraints}"""),
])


# ── Rephrase ──────────────────────────────────────────────────────────────────

CODING_REPHRASE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert competitive programming problem writer.
Rewrite the coding problem statement using completely different vocabulary and
sentence structure. 

STRICT RULES:
1. ALL test cases stay IDENTICAL — same input values, same expected outputs
2. Keep function signature the same if provided; if missing/empty, infer one from question/test-case argument names
3. The algorithm required is UNCHANGED
4. Only rephrase the problem description text
5. Return ONLY a JSON object with keys:
   - "question": rewritten problem text
   - "function_signature": function signature to use
No markdown fences."""),
    ("human", """Original Question: {question}
Algorithm: {algorithm_category}
Core Logic: {core_logic}
Current Function Signature (may be empty): {function_signature}"""),
])


# ── Contextual ────────────────────────────────────────────────────────────────

CODING_CONTEXTUAL_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert competitive programming problem writer.
Rewrite this coding problem by wrapping the same algorithm in a real-world scenario.

Examples of domain shifts:
  - Two Sum → "find two products whose prices sum to a budget"
  - Reverse Linked List → "undo a sequence of customer orders"
  - Binary Search → "find a specific temperature reading in sorted sensor data"

RULES:
1. Same algorithm: {algorithm_category}
2. Same test case VALUES (adapt variable names only to match new domain)
3. Same expected outputs
4. If current function signature is empty, infer one based on renamed input args in test cases
5. Return ONLY a JSON object with keys:
   - "question": new problem text with real-world context
   - "test_cases": same test cases with domain-appropriate variable names
   - "function_signature": updated function name matching new domain
No markdown fences."""),
    ("human", """Original Question: {question}
Test Cases (JSON): {test_cases}
Algorithm Category: {algorithm_category}
Core Logic: {core_logic}
Current Function Signature (may be empty): {function_signature}"""),
])


# ── Difficulty ────────────────────────────────────────────────────────────────

CODING_DIFFICULTY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert competitive programming problem writer.
Modify the difficulty of this problem from level {current_level} to level {target_level} (1-5).
Direction: {direction}

If making HARDER:
  - Add an extra dimension (2D instead of 1D, k-sum instead of 2-sum)
  - Add follow-up constraints (return all solutions, not just one)
  - Require optimal complexity
  - Add edge case requirements

If making EASIER:
  - Reduce dimensionality
  - Guarantee sorted input
  - Reduce to a single-pass problem
  - Allow brute force solution

RULES:
1. Generate a COMPLETE new problem statement
2. Generate {tc_count} NEW test cases with correct inputs AND outputs
3. If no signature is provided, infer one from generated test-case input args
4. Return ONLY a JSON object with keys:
   - "question": new problem text
   - "test_cases": dict of {{"tc_1": {{"input": ..., "output": ..., "category": "basic"}}, ...}}
   - "function_signature": new function signature
   - "explanation": one sentence on what you changed
No markdown fences."""),
    ("human", """Original Question: {question}
Original Test Cases: {test_cases}
Algorithm: {algorithm_category}
Time Complexity: {time_complexity}
Current Difficulty Level: {current_level}
Target Difficulty Level: {target_level}
Current Function Signature (may be empty): {function_signature}"""),
])


# ── Constraint morph ──────────────────────────────────────────────────────────

CODING_CONSTRAINT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert competitive programming problem writer.
Add a complexity constraint to this problem that forces a different algorithm approach.

Constraint type: {constraint_type}

Examples:
  - space: "Must use O(1) extra space" (forces in-place or two-pointer)
  - time: "Must solve in O(n log n) or better" (forces sorting/binary search)
  - no_builtin: "Cannot use built-in sort functions"
  - single_pass: "Must solve in a single pass through the array"

RULES:
1. Problem core stays the same
2. Test case INPUTS stay the same (may need minor adjustment for new constraint)
3. Test case OUTPUTS stay the same
4. The new constraint must make the previous O(n²) brute-force approach invalid
5. Keep function signature the same if provided; if empty, infer one from input args
6. Return ONLY a JSON object with keys:
   - "question": original problem + added constraint paragraph
   - "test_cases": same test cases (adjust inputs only if constraint requires, e.g. sorted input)
   - "constraints": {{"time_complexity": "...", "space_complexity": "...", "notes": [...]}}
    - "function_signature": function signature to use
No markdown fences."""),
    ("human", """Original Question: {question}
Test Cases: {test_cases}
Algorithm: {algorithm_category}
Current Function Signature (may be empty): {function_signature}
Constraint Type: {constraint_type}"""),
])


# ── TC Generation ─────────────────────────────────────────────────────────────

CODING_TCGEN_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert competitive programming test case designer.
Generate {n_new} NEW test cases for this problem targeting specific coverage areas.
The existing test cases are already provided — do NOT duplicate them.

Coverage targets for new test cases:
- Edge cases: empty input, single element, all same values
- Boundary values: min/max possible values per constraints
- Negative numbers if applicable
- Large values (not stress test — just larger than trivial)
- Cases where naive solutions fail (e.g. duplicates, zeros, negatives)

RULES:
1. The existing test cases are KEPT — you only ADD new ones
2. Every new test case MUST have a verified correct output
3. Label categories: "edge_case", "boundary", "stress"
4. Keep function signature the same if provided; if empty, infer one from test-case input args
5. Return ONLY a JSON object with keys:
    - "new_test_cases":
   dict of {{"tc_N": {{"input": ..., "output": ..., "category": "...", "explanation": "..."}}}}
    - "function_signature": function signature to use
No markdown fences."""),
    ("human", """Question: {question}
Algorithm: {algorithm_category}
Core Logic: {core_logic}
Existing Test Cases (do NOT duplicate): {test_cases}
Current Function Signature (may be empty): {function_signature}
Number of new TCs to generate: {n_new}"""),
])


# ── TC Scaling ────────────────────────────────────────────────────────────────

CODING_TCSCALE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert competitive programming test case designer.
Generate {n_stress} stress/performance test cases for this problem.
These test cases have LARGE inputs designed to catch solutions with bad time complexity.

The best solution has time complexity: {time_complexity}
A naive/brute-force solution would be: {naive_complexity}

Generate test cases where:
- Input size n >= 10000
- The correct answer is mathematically guaranteed and computable
- Use structured inputs (e.g. range(10000), known pairs) not random
- Include the expected output

RULES:
1. Existing test cases are KEPT — only ADD stress tests
2. Every stress test MUST include the correct verified output
3. Label all as category: "stress"
4. Keep function signature the same if provided; if empty, infer one from test-case input args
5. Return ONLY a JSON object with keys:
    - "stress_test_cases":
   dict of {{"stress_1": {{"input": ..., "output": ..., "category": "stress", "explanation": "n=10000 test"}}}}
    - "function_signature": function signature to use
No markdown fences."""),
    ("human", """Question: {question}
Algorithm: {algorithm_category}
Best Time Complexity: {time_complexity}
Test Cases to Scale Up From: {test_cases}
Current Function Signature (may be empty): {function_signature}
Number of stress tests: {n_stress}"""),
])


# ── TC Validator (answer check) ───────────────────────────────────────────────

CODING_TC_VERIFY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert competitive programmer and test case verifier.
For each test case provided, verify that the expected output is mathematically correct
for the given problem.

Return ONLY a JSON object with key "results":
  list of {{"tc_name": "tc_1", "is_correct": true, "expected": "...", "reason": "..."}}
No markdown fences."""),
    ("human", """Problem: {question}
Algorithm: {algorithm_category}
Test Cases to Verify: {test_cases}"""),
])