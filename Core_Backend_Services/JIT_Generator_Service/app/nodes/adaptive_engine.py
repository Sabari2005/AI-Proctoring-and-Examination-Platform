"""
JIT/app/nodes/adaptive_engine.py
──────────────────────────────────
Adaptive engine node.  Called once per cycle after answer evaluation.

Responsibility:
  1. Update theta using a simple IRT-inspired update rule
  2. Choose the next difficulty level (clamped to 1-5)
  3. Choose the next sub-topic (cycle through queue, boost struggling topics)
  4. Update streak / consecutive-wrong counters
  5. Update sub-topic mastery
  6. Decide whether the session is done (questions_asked >= num_questions)
  7. Return updated session state + AdaptiveDecision
"""
from app.core.state import JITGraphState
from app.core.schemas import AdaptiveDecision, QuestionRecord
from app.core.enums import DifficultyLevel, AnswerStatus, DIFFICULTY_TO_BLOOM
from app.core.config import settings


def adaptive_engine(state: JITGraphState) -> dict:
    session    = state["session"]
    question   = state["current_question"]
    evaluation = state["current_evaluation"]
    submission = state["current_submission"]
    config     = session.config

    prev_theta       = session.theta
    prev_difficulty  = session.current_difficulty
    prev_sub_topic   = session.current_sub_topic
    status           = evaluation.status
    score            = evaluation.score

    learning_rate    = config.learning_rate

    # ── 1. Update theta ───────────────────────────────────────────────────
    # Correct or partial pushes theta up; wrong pushes it down.
    if status == AnswerStatus.CORRECT:
        delta = learning_rate * (1.0 - score * 0.1)     # big + for fast correct
    elif status == AnswerStatus.PARTIAL:
        delta = learning_rate * 0.3 * score
    else:
        delta = -learning_rate * (1.0 - score)

    new_theta = max(1.0, min(5.0, prev_theta + delta))

    # ── 2. Streak / consecutive-wrong tracking ────────────────────────────
    if status == AnswerStatus.CORRECT:
        streak          = session.streak + 1
        consecutive_wrong = 0
    elif status == AnswerStatus.PARTIAL:
        streak          = max(0, session.streak - 1)
        consecutive_wrong = 0
    else:
        streak          = 0
        consecutive_wrong = session.consecutive_wrong + 1

    # ── 3. Next difficulty ───────────────────────────────────────────────
    theta_diff = int(round(new_theta))
    theta_diff = max(1, min(5, theta_diff))

    max_jump   = settings.MAX_DIFFICULTY_JUMP
    cur_val    = prev_difficulty.value
    next_val   = max(cur_val - max_jump, min(cur_val + max_jump, theta_diff))
    next_val   = max(1, min(5, next_val))

    # Streak bonus — allow one extra difficulty jump up
    if streak >= settings.STREAK_THRESHOLD and next_val < 5:
        next_val = min(5, next_val + 1)

    # Lock down after consecutive wrong
    if consecutive_wrong >= settings.LOCK_AFTER_WRONG and next_val > 1:
        next_val = max(1, next_val - 1)

    next_difficulty = DifficultyLevel(next_val)
    reason_parts    = []
    if next_val > cur_val:
        reason_parts.append(f"levelling up (theta={new_theta:.2f})")
    elif next_val < cur_val:
        reason_parts.append(f"levelling down (theta={new_theta:.2f})")
    else:
        reason_parts.append(f"maintaining level (theta={new_theta:.2f})")
    if streak >= settings.STREAK_THRESHOLD:
        reason_parts.append(f"streak={streak}")
    if consecutive_wrong >= settings.LOCK_AFTER_WRONG:
        reason_parts.append(f"consecutive_wrong={consecutive_wrong}")

    # ── 4. Sub-topic mastery update ──────────────────────────────────────
    mastery = dict(session.sub_topic_mastery)
    sub     = question.sub_topic
    prev_m  = mastery.get(sub, 50.0)

    if status == AnswerStatus.CORRECT:
        new_m = min(100.0, prev_m + 10.0 * score)
    elif status == AnswerStatus.PARTIAL:
        new_m = min(100.0, prev_m + 4.0 * score)
    else:
        new_m = max(0.0, prev_m - 8.0)

    mastery[sub] = round(new_m, 1)

    # ── 5. Next sub-topic ────────────────────────────────────────────────
    queue = list(session.sub_topic_queue)
    if queue:
        # Prefer weakest sub-topic that hasn't just been asked
        weak_topics = sorted(
            [t for t in queue if t != sub],
            key=lambda t: mastery.get(t, 50.0),
        )
        # Re-visit current topic if it's still very weak (mastery < 40)
        if not weak_topics or new_m < 40.0:
            next_sub_topic = sub
        else:
            next_sub_topic = weak_topics[0]
    else:
        next_sub_topic = sub

    # ── 6. Bloom level tracking ──────────────────────────────────────────
    bloom_levels = list(session.bloom_levels_reached)
    if status in (AnswerStatus.CORRECT, AnswerStatus.PARTIAL):
        bl = DIFFICULTY_TO_BLOOM[question.difficulty]
        if bl not in bloom_levels:
            bloom_levels.append(bl)

    # ── 7. Persist question record ────────────────────────────────────────
    record = QuestionRecord(
        question=question,
        submission=submission,
        evaluation=evaluation,
        decision=AdaptiveDecision(
            prev_theta=round(prev_theta, 3),
            new_theta=round(new_theta, 3),
            theta_delta=round(delta, 3),
            next_difficulty=next_difficulty,
            next_sub_topic=next_sub_topic,
            next_qtype=session.current_qtype,
            streak=streak,
            reason="; ".join(reason_parts),
        ),
    )

    session.question_history.append(record)
    session.questions_asked    = session.questions_asked + 1
    session.theta              = round(new_theta, 3)
    session.current_difficulty = next_difficulty
    session.current_sub_topic  = next_sub_topic
    session.streak             = streak
    session.consecutive_wrong  = consecutive_wrong
    session.sub_topic_mastery  = mastery
    session.bloom_levels_reached = bloom_levels
    session.difficulty_trajectory.append(question.difficulty.value)

    # ── 8. Check session completion ───────────────────────────────────────
    action = "report" if session.questions_asked >= config.num_questions else "generate"

    decision = record.decision

    print(
        f"[adaptive_engine] Q{session.questions_asked} | {status.value} | "
        f"theta {prev_theta:.2f}→{new_theta:.2f} | "
        f"diff {prev_difficulty.value}→{next_difficulty.value} | "
        f"streak={streak} | sub_topic='{next_sub_topic}' | action={action}"
    )

    return {
        "session":          session,
        "current_decision": decision,
        "action":           action,
    }
