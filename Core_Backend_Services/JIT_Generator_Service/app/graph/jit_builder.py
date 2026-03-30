"""
JIT/app/graph/jit_builder.py
─────────────────────────────
Assembles the JIT adaptive assessment LangGraph.

Topology:
  START
    → extract_subtopics
    → generate_question           ← loops back here after adapt
    → [PAUSE — wait for answer via API]
    → evaluate_answer
    → adaptive_engine
        ├─ more questions → generate_question
        └─ done → report_generator → END
"""
from langgraph.graph import StateGraph, START, END
from app.core.state import JITGraphState
from app.nodes.subtopic_extractor import extract_subtopics
from app.nodes.question_generator import question_generator
from app.nodes.adaptive_engine import adaptive_engine
from app.nodes.report_generator import report_generator


def route_after_adapt(state: JITGraphState) -> str:
    """After adaptive engine: more questions or final report."""
    return "report_generator" if state["action"] == "report" else "question_generator"


def build_jit_graph():
    builder = StateGraph(JITGraphState)

    builder.add_node("extract_subtopics",  extract_subtopics)
    builder.add_node("question_generator", question_generator)
    builder.add_node("adaptive_engine",    adaptive_engine)
    builder.add_node("report_generator",   report_generator)

    builder.add_edge(START,                "extract_subtopics")
    builder.add_edge("extract_subtopics",  "question_generator")

    # After adaptive engine: loop or end
    builder.add_conditional_edges(
        "adaptive_engine",
        route_after_adapt,
        {
            "question_generator": "question_generator",
            "report_generator":   "report_generator",
        },
    )

    builder.add_edge("report_generator", END)

    # NOTE: question_generator does NOT have an outgoing edge here
    # because the graph pauses and waits for an answer submission via API.
    # The evaluate_answer node is called externally via the service layer,
    # then adaptive_engine is called to continue the graph.
    # In the streaming/agentic mode, the graph compiles with interrupt_after.

    return builder.compile(
        interrupt_after=["question_generator"],   # pause here, wait for answer
    )


jit_graph = build_jit_graph()