import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session
from enum import Enum as _Enum

from app.core.coding_state import CodingMorphState
from app.core.qtype_enums import QType
from app.core.qtype_state import QTypeMorphState
from app.core.state import MorphState
from app.graph.coding_builder import coding_morph_graph
from app.graph.qtype_builder import qtype_graph
from app.graph.builder import morph_graph

from server.models import (
    Candidate,
    Drive,
    DriveRegistration,
    ExamSection,
    LLMQuestionVariant,
    LLMRegistrationJob,
    Question,
)
from server.services.input_mapper import build_input_from_question


class ProcessingSummary(dict):
    pass


def _normalize_enum_like(value: Any, max_len: int = 64) -> str:
    if value is None:
        return ""

    raw = getattr(value, "value", value)
    text = str(raw).strip()
    if "." in text:
        text = text.split(".")[-1]
    return text[:max_len]


def _build_mcq_state(inp: Any) -> MorphState:
    return {
        "input": inp,
        "trace_id": "",
        "analysis_result": None,
        "difficulty_target": None,
        "bloom_target": None,
        "morphed_variants": [],
        "validation_report": None,
        "retry_count": 0,
        "current_strategy": None,
        "final_output": None,
        "error": None,
    }


def _build_qtype_state(inp: Any, qtype: QType) -> QTypeMorphState:
    return {
        "input": inp,
        "qtype": qtype,
        "trace_id": "",
        "analysis_result": None,
        "difficulty_target": None,
        "bloom_target": None,
        "morphed_variants": [],
        "validation_report": None,
        "retry_count": 0,
        "current_strategy": None,
        "final_output": None,
        "error": None,
    }


def _build_coding_state(inp: Any) -> CodingMorphState:
    return {
        "input": inp,
        "trace_id": "",
        "analysis_result": None,
        "difficulty_target": None,
        "bloom_target": None,
        "morphed_variants": [],
        "validation_report": None,
        "retry_count": 0,
        "current_strategy": None,
        "final_output": None,
        "error": None,
    }


async def _invoke_graph(normalized_qtype: str, inp: Any) -> dict[str, Any] | None:
    if normalized_qtype == "mcq":
        state = _build_mcq_state(inp)
        result = await morph_graph.ainvoke(state)
        return result.get("final_output")

    if normalized_qtype == "coding":
        state = _build_coding_state(inp)
        result = await coding_morph_graph.ainvoke(state)
        return result.get("final_output")

    qtype_map = {
        "fib": QType.FIB,
        "short": QType.SHORT,
        "msq": QType.MSQ,
        "numerical": QType.NUMERICAL,
        "long": QType.LONG,
    }

    qtype = qtype_map.get(normalized_qtype)
    if not qtype:
        return None

    state = _build_qtype_state(inp, qtype)
    result = await qtype_graph.ainvoke(state)
    return result.get("final_output")


def _ensure_registration_context(db: Session, candidate_id: int, exam_id: int) -> None:
    candidate = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
    if not candidate:
        raise ValueError(f"candidate_id {candidate_id} not found")

    exam = db.query(Drive).filter(Drive.drive_id == exam_id).first()
    if not exam:
        raise ValueError(f"exam_id {exam_id} not found")

    registration = (
        db.query(DriveRegistration)
        .filter(DriveRegistration.candidate_id == candidate_id, DriveRegistration.drive_id == exam_id)
        .first()
    )
    if not registration:
        raise ValueError("candidate is not registered for this exam")


def _load_questions_for_exam(db: Session, exam_id: int) -> list[tuple[Any, Question]]:
    sections = (
        db.query(ExamSection)
        .filter(ExamSection.drive_id == exam_id)
        .order_by(ExamSection.order_index.asc(), ExamSection.section_id.asc())
        .all()
    )

    rows: list[tuple[Any, Question]] = []
    for section in sections:
        questions = (
            db.query(Question)
            .filter(Question.drive_id == exam_id, Question.section_id == section.section_id)
            .order_by(Question.question_id.asc())
            .all()
        )
        for question in questions:
            rows.append((section.section_id, question))
    return rows


def _start_or_reset_job(db: Session, candidate_id: int, exam_id: int) -> LLMRegistrationJob:
    job = (
        db.query(LLMRegistrationJob)
        .filter(LLMRegistrationJob.candidate_id == candidate_id, LLMRegistrationJob.exam_id == exam_id)
        .first()
    )

    if not job:
        job = LLMRegistrationJob(candidate_id=candidate_id, exam_id=exam_id)
        db.add(job)
        db.flush()

    db.query(LLMQuestionVariant).filter(
        LLMQuestionVariant.candidate_id == candidate_id,
        LLMQuestionVariant.exam_id == exam_id,
    ).delete(synchronize_session=False)

    setattr(job, "status", "processing")
    setattr(job, "processed_questions", 0)
    setattr(job, "created_variants", 0)
    setattr(job, "error_message", None)
    setattr(job, "started_at", datetime.now(timezone.utc))
    setattr(job, "finished_at", None)

    db.flush()
    return job



def _serialize_variant(variant: dict[str, Any]) -> str:
    """
    Serialize a morphed variant dict to a JSON string suitable for DB storage.

    Handles all non-standard types that come out of the morphing graphs:
      - Enum  (DifficultyLevel, MorphType, QType, BloomLevel, AnswerStatus …)
            → stored as their .value (int or str)
      - datetime → ISO-8601 string
      - set, frozenset → sorted list
      - Everything else → str() fallback
    
    Native JSON types (dict, list, int, float, bool, str, None) are passed
    through unchanged, so list/int/dict test-case inputs are preserved exactly.
    """
    def _default(obj):
        if isinstance(obj, _Enum):
            return obj.value          # DifficultyLevel.VERY_HARD → 5
        if hasattr(obj, "isoformat"):  # datetime, date
            return obj.isoformat()
        if isinstance(obj, (set, frozenset)):
            return sorted(str(x) for x in obj)
        return str(obj)               # last-resort fallback

    return json.dumps(variant, default=_default, ensure_ascii=False)

def _store_variants(
    db: Session,
    job: LLMRegistrationJob,
    candidate_id: int,
    exam_id: int,
    section_id: int,
    source_question: Question,
    output: dict[str, Any],
) -> int:
    variants = output.get("variants", [])
    print("------------------------------------------------------------------------------")
    print(variants)
    print("------------------------------------------------------------------------------")
    trace_id = str(output.get("trace_id", ""))
    count = 0

    for idx, variant in enumerate(variants, start=1):
        # Extract column values from enum/string fields before serializing payload
        morph_type_raw      = variant.get("morph_type")
        difficulty_raw      = variant.get("difficulty_actual")
        source_qtype_raw    = source_question.question_type

        morph_type        = _normalize_enum_like(morph_type_raw,   max_len=80)
        difficulty_actual = _normalize_enum_like(difficulty_raw,   max_len=64)
        source_qtype      = _normalize_enum_like(source_qtype_raw, max_len=50) or "MCQ"

        # Serialize the full variant payload preserving native types
        # (list/int/dict test-case inputs stay as-is; Enums → .value)
        try:
            payload_json = _serialize_variant(variant)
        except Exception as serialize_exc:
            # Absolute fallback — should never trigger after _serialize_variant
            print(f"[_store_variants] serialize error on variant {idx}: {serialize_exc}")
            payload_json = json.dumps(
                {k: str(v) for k, v in variant.items()},
                ensure_ascii=False,
            )

        row = LLMQuestionVariant(
            job_id                = job.job_id,
            candidate_id          = candidate_id,
            exam_id               = exam_id,
            section_id            = section_id,
            source_question_id    = source_question.question_id,
            source_question_type  = source_qtype,
            variant_index         = idx,
            morph_type            = morph_type,
            trace_id              = trace_id,
            semantic_score        = float(variant.get("semantic_score", 0.0) or 0.0),
            difficulty_actual     = difficulty_actual,
            payload_json          = payload_json,
            selected_for_exam     = True,
        )
        db.add(row)
        count += 1

    return count

async def process_registration(candidate_id: int, exam_id: int, db: Session) -> ProcessingSummary:
    _ensure_registration_context(db, candidate_id, exam_id)

    job = _start_or_reset_job(db, candidate_id, exam_id)
    db.commit()

    processed_questions = 0
    created_variants = 0
    skipped_questions = 0

    try:
        items = _load_questions_for_exam(db, exam_id)
        print(items)

        for section_id, question in items:
            # print(question)
            normalized_qtype, graph_input = build_input_from_question(question)
            # print(normalized_qtype, graph_input)

            if not normalized_qtype or graph_input is None:
                skipped_questions += 1
                continue

            output = await _invoke_graph(normalized_qtype, graph_input)
            if not output:
                skipped_questions += 1
                continue

            processed_questions += 1
            created_variants += _store_variants(
                db=db,
                job=job,
                candidate_id=candidate_id,
                exam_id=exam_id,
                section_id=section_id,
                source_question=question,
                output=output,
            )

        setattr(job, "status", "completed")
        setattr(job, "processed_questions", processed_questions)
        setattr(job, "created_variants", created_variants)
        setattr(job, "error_message", None)
        setattr(job, "finished_at", datetime.now(timezone.utc))
        db.commit()

        return ProcessingSummary(
            status=job.status,
            job_id=job.job_id,
            processed_questions=processed_questions,
            created_variants=created_variants,
            skipped_questions=skipped_questions,
        )

    except Exception as exc:
        db.rollback()

        failed_job = (
            db.query(LLMRegistrationJob)
            .filter(LLMRegistrationJob.job_id == job.job_id)
            .first()
        )
        if failed_job:
            setattr(failed_job, "status", "failed")
            setattr(failed_job, "error_message", str(exc))
            setattr(failed_job, "processed_questions", processed_questions)
            setattr(failed_job, "created_variants", created_variants)
            setattr(failed_job, "finished_at", datetime.now(timezone.utc))
            db.commit()

        return ProcessingSummary(
            status="failed",
            job_id=job.job_id,
            processed_questions=processed_questions,
            created_variants=created_variants,
            skipped_questions=skipped_questions,
            detail=str(exc),
        )
