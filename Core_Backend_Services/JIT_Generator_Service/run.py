"""
JIT/run.py
───────────
CLI runner for a full interactive JIT adaptive assessment session.
Simulates the real API flow in your terminal.

Usage:
    python run.py
    python run.py --topic "Python Basics" --questions 5 --type mcq
    python run.py --topic "Operating Systems" --questions 8 --type mixed
    python run.py --topic "Data Structures" --questions 6 --type coding
"""
import argparse
import json
import time
from dotenv import load_dotenv

load_dotenv()

from app.core.schemas import JITSessionConfig, AnswerSubmission
from app.core.enums import QType, DifficultyLevel
from app.api.jit_service import start_session, submit_answer


def format_question(q: dict, q_num: int, total: int) -> None:
    qtype = q.get("qtype", "mcq")
    diff  = q.get("difficulty", 3)
    diff_labels = {1:"Very Easy", 2:"Easy", 3:"Medium", 4:"Hard", 5:"Very Hard"}

    print(f"\n{'='*65}")
    print(f"  Question {q_num}/{total}  |  {qtype.upper()}  |  {diff_labels.get(diff,'?')} (Level {diff})")
    print(f"  Sub-topic: {q.get('sub_topic','')}  |  Bloom: {q.get('bloom_level','').capitalize()}")
    print(f"  Expected time: {q.get('expected_time_seconds',60)}s")
    print(f"{'='*65}")
    print(f"\n  {q.get('question_text','')}\n")

    if qtype == "mcq" and q.get("options"):
        for opt in q["options"]:
            print(f"  {opt}")

    elif qtype == "msq" and q.get("options"):
        print("  (Select ALL correct answers — enter letters separated by commas, e.g. A,C)")
        for opt in q["options"]:
            print(f"  {opt}")

    elif qtype == "fib":
        print("  (Fill in the blank — type your answer)")

    elif qtype == "numerical":
        print(f"  (Enter a number — unit: {q.get('unit','')})")

    elif qtype == "short":
        wl = q.get("word_limit") or {}
        print(f"  (Short answer — {wl.get('min',10)} to {wl.get('max',100)} words)")

    elif qtype == "long":
        wl = q.get("word_limit") or {}
        print(f"  (Long answer — {wl.get('min',200)} to {wl.get('max',800)} words)")
        rubric = q.get("rubric") or {}
        points = rubric.get("points", [])
        if points:
            print("\n  Rubric:")
            for pt in points:
                print(f"    • {pt.get('point','')} [{pt.get('marks',0)} marks]")

    elif qtype == "coding":
        print(f"  Function: {q.get('function_signature','')}")
        print("\n  Test Cases:")
        for name, tc in list(q.get("test_cases", {}).items())[:3]:
            print(f"    {name}: input={tc.get('input',{})} → output={tc.get('output','?')}")
        print("\n  (Enter your code below. Type END on a new line when done.)")

    if q.get("hints"):
        print(f"\n  Hint available (type 'hint' to reveal)")

    print()


def get_answer(qtype: str, hints: list) -> tuple:
    """Get answer from terminal input. Returns (answer, time_taken, confidence)."""
    start = time.time()

    if qtype == "coding":
        print("  Your code:")
        lines = []
        while True:
            line = input("  ")
            if line.strip().upper() == "END":
                break
            if line.strip().lower() == "hint" and hints:
                print(f"  Hint: {hints[0]}")
                continue
            lines.append(line)
        answer = "\n".join(lines)
    elif qtype == "long":
        print("  Your answer (type END on a new line to finish):")
        lines = []
        while True:
            line = input("  ")
            if line.strip().upper() == "END":
                break
            lines.append(line)
        answer = "\n".join(lines)
    elif qtype == "msq":
        raw = input("  Your selections (e.g. A,B,C): ").strip()
        if raw.lower() == "hint" and hints:
            print(f"  Hint: {hints[0]}")
            raw = input("  Your selections: ").strip()
        # Convert letter selections to full option strings
        answer = [s.strip().upper() for s in raw.split(",")]
    else:
        raw = input("  Your answer: ").strip()
        if raw.lower() == "hint" and hints:
            print(f"  Hint: {hints[0]}")
            raw = input("  Your answer: ").strip()
        answer = raw

    elapsed = int(time.time() - start)

    # Confidence rating
    try:
        conf_raw = input("  Confidence (1-5, or Enter to skip): ").strip()
        confidence = int(conf_raw) if conf_raw else None
    except (ValueError, EOFError):
        confidence = None

    return answer, elapsed, confidence


def print_evaluation(eval_dict: dict, decision_dict: dict) -> None:
    status = eval_dict.get("status", "")
    score  = eval_dict.get("score", 0)
    icons  = {"correct": "✓", "partial": "~", "wrong": "✗",
              "skipped": "-", "timeout": "T"}

    print(f"\n  {icons.get(status,'?')} {status.upper()}  |  Score: {score:.0%}")
    print(f"  {eval_dict.get('feedback','')}")

    reveal = eval_dict.get("correct_answer_reveal")
    if reveal and status != "correct":
        print(f"  Correct answer: {reveal}")

    tr = eval_dict.get("time_ratio", 1.0)
    speed = "fast" if tr < 0.7 else ("slow" if tr > 1.3 else "on time")
    print(f"  Time: {speed} ({tr:.1f}x expected)")

    d = decision_dict or {}
    print(f"\n  Theta: {d.get('prev_theta',0):.2f} → {d.get('new_theta',0):.2f}  "
          f"|  Next difficulty: {d.get('next_difficulty',2)}/5  "
          f"|  Streak: {d.get('streak',0)}")
    if d.get("reason"):
        print(f"  Reason: {d['reason']}")


def print_report(report: dict) -> None:
    print(f"\n{'='*65}")
    print(f"  FINAL ASSESSMENT REPORT")
    print(f"{'='*65}")
    print(f"  Candidate   : {report.get('candidate_id')}")
    print(f"  Topic       : {report.get('section_topic')}")
    print(f"  Score       : {report.get('accuracy')}%  ({report.get('correct')} correct, "
          f"{report.get('partial')} partial, {report.get('wrong')} wrong)")
    print(f"  Theta       : {report.get('theta_final')} → {report.get('skill_label')}")
    print(f"  Bloom level : {report.get('highest_bloom','').capitalize()}")
    print(f"  Speed       : {report.get('speed_profile')}")

    traj = report.get("difficulty_trajectory", [])
    if traj:
        print(f"  Trajectory  : {' → '.join(str(d) for d in traj)}")

    mastery = report.get("sub_topic_mastery", {})
    attempts = report.get("sub_topic_attempts", {})
    if mastery:
        print(f"\n  Sub-topic mastery:")
        for topic, score in sorted(mastery.items(), key=lambda x: (-x[1], -attempts.get(x[0], 0))):
            bar = "█" * int(score / 10) + "░" * (10 - int(score / 10))
            n = attempts.get(topic, 0)
            print(f"    {topic[:30]:<30} {bar} {score:.0f}% (n={n})")

    strengths = report.get("strengths", [])
    if strengths:
        print(f"\n  Strengths: {', '.join(strengths[:3])}")

    weaknesses = report.get("weaknesses", [])
    if weaknesses:
        print(f"  Weaknesses: {', '.join(weaknesses[:3])}")

    recs = report.get("recommendations", [])
    if recs:
        print(f"\n  Recommendations:")
        for r in recs[:3]:
            print(f"    • {r}")

    print(f"\n{'='*65}\n")


def run_session(topic: str, num_questions: int, qtype: str, difficulty: int) -> None:
    config = JITSessionConfig(
        section_topic=topic,
        num_questions=num_questions,
        question_type=QType(qtype),
        start_difficulty=DifficultyLevel(difficulty),
        candidate_id="cli_user",
    )

    print(f"\n  Starting JIT session...")
    print(f"  Topic: {topic} | Questions: {num_questions} | Type: {qtype}")

    # Start session
    response = start_session(config)
    session_id = response.session_id
    question   = response.first_question

    print(f"  Session ID: {session_id}")
    print(f"  Sub-topics: {', '.join(response.session_info.get('sub_topics', [])[:4])}...")

    q_num = 1
    while True:
        q_dict = question.model_dump()
        format_question(q_dict, q_num, num_questions)

        answer, elapsed, confidence = get_answer(question.qtype.value, question.hints)

        submission = AnswerSubmission(
            session_id=session_id,
            question_id=question.question_id,
            question_number=question.question_number,
            answer=answer,
            time_taken_seconds=elapsed,
            confidence=confidence,
        )

        result = submit_answer(submission)
        print_evaluation(
            result.evaluation.model_dump(),
            result.adaptive_decision.model_dump() if result.adaptive_decision else {},
        )

        if result.session_complete:
            print_report(result.final_report)
            # Save report
            fname = f"jit_report_{session_id}.json"
            with open(fname, "w") as f:
                json.dump(result.final_report, f, indent=2, default=str)
            print(f"  Report saved → {fname}")
            break

        question = result.next_question
        q_num   += 1
        input("\n  Press Enter for next question...")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="JIT Adaptive Assessment CLI")
    parser.add_argument("--topic",     default="Operating Systems",
                        help="Section topic (e.g. 'Python Basics')")
    parser.add_argument("--questions", type=int, default=5,
                        help="Number of questions (3-50)")
    parser.add_argument("--type",      default="mcq",
                        choices=["mcq","fib","short","msq","numerical","long","coding","mixed"],
                        help="Question type")
    parser.add_argument("--difficulty", type=int, default=2, choices=[1,2,3,4,5],
                        help="Starting difficulty (1=very easy, 5=very hard)")
    args = parser.parse_args()

    run_session(args.topic, args.questions, args.type, args.difficulty)