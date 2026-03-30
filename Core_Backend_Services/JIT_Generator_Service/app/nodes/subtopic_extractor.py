"""
JIT/app/nodes/subtopic_extractor.py
─────────────────────────────────────
Extracts sub-topics from section_topic if none provided.
Called once at session start.
"""
from app.core.state import JITGraphState
from app.llm.providers import invoke_with_fallback
from app.llm.prompts import SUBTOPIC_PROMPT
from app.utils.json_parser import parse_llm_json


# Fallback sub-topics per common section topics
FALLBACK_SUBTOPICS = {
    "operating system": [
        "Process Management", "Thread Synchronization", "Memory Management",
        "Virtual Memory", "File Systems", "I/O Management",
        "Scheduling Algorithms", "Deadlocks",
    ],
    "python": [
        "Data Types", "Control Flow", "Functions", "OOP",
        "List Comprehensions", "Error Handling", "Modules", "File I/O",
    ],
    "default": [
        "Fundamentals", "Core Concepts", "Applications",
        "Advanced Topics", "Problem Solving", "Case Studies",
    ],
}


def extract_subtopics(state: JITGraphState) -> dict:
    session = state["session"]
    config  = session.config

    # If sub-topics already provided, use them
    if config.sub_topics:
        queue = list(config.sub_topics)
        print(f"[subtopic_extractor] Using provided sub-topics: {queue}")
    else:
        # Try LLM extraction
        try:
            raw  = invoke_with_fallback(SUBTOPIC_PROMPT.format_messages(
                section_topic=config.section_topic
            ))
            data = parse_llm_json(raw)
            queue = data.get("sub_topics", [])
            if not queue:
                raise ValueError("Empty sub-topics from LLM")
        except Exception as e:
            print(f"[subtopic_extractor] LLM failed: {e}. Using fallback.")
            key   = config.section_topic.lower()
            queue = FALLBACK_SUBTOPICS["default"]
            for fallback_key, fallback_topics in FALLBACK_SUBTOPICS.items():
                if fallback_key != "default" and fallback_key in key:
                    queue = fallback_topics
                    break

    # Initialise mastery map
    mastery = {st: 00.0 for st in queue}   # start at 50% (neutral)

    session.sub_topic_queue   = queue
    session.sub_topic_mastery = mastery
    session.current_sub_topic = queue[0] if queue else config.section_topic
    session.current_qtype     = config.question_type
    session.current_difficulty = config.start_difficulty
    session.theta             = float(config.start_difficulty.value)

    print(
        f"[subtopic_extractor] {len(queue)} sub-topics for '{config.section_topic}': {queue[:4]}..."
    )
    return {"session": session, "action": "generate"}