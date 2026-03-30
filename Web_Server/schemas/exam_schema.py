from typing import Any

from pydantic import BaseModel


class JitSectionInput(BaseModel):
    topic: str
    count: int
    question_type: str = "mcq"


class CreateExamRequest(BaseModel):
    title: str
    exam_type: str
    duration_minutes: int
    max_attempts: int
    description: str | None = None
    generation_mode: str = "static"
    jit_sections: list[JitSectionInput] | None = None
    eligibility: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    exam_date: str | None = None
    max_marks: int | None = None
    is_published: bool = False
    key_topics: list[str] | None = None
    specializations: list[str] | None = None


class UpdateExamRequest(BaseModel):
    title: str | None = None
    exam_type: str | None = None
    duration_minutes: int | None = None
    max_attempts: int | None = None
    description: str | None = None
    generation_mode: str | None = None
    status: str | None = None
    is_published: bool | None = None
    eligibility: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    exam_date: str | None = None
    max_marks: int | None = None
    key_topics: list[str] | None = None
    specializations: list[str] | None = None


class CreateSectionRequest(BaseModel):
    title: str
    section_type: str = "mixed"
    order_index: int | None = None
    marks_weight: int | None = None
    status: str = "draft"


class UpdateSectionRequest(BaseModel):
    title: str | None = None
    section_type: str | None = None
    order_index: int | None = None
    marks_weight: int | None = None
    status: str | None = None


class CreateQuestionRequest(BaseModel):
    question_text: str
    question_type: str = "MCQ"
    marks: int = 1
    taxonomy_level: int = 3
    morphing_strategy: str | None = None
    time_complexity: str | None = None
    space_complexity: str | None = None
    payload: dict[str, Any] | None = None


class UpdateQuestionRequest(BaseModel):
    question_text: str | None = None
    question_type: str | None = None
    marks: int | None = None
    taxonomy_level: int | None = None
    morphing_strategy: str | None = None
    time_complexity: str | None = None
    space_complexity: str | None = None
    payload: dict[str, Any] | None = None
