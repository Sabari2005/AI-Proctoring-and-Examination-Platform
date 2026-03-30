from pydantic import BaseModel, Field


class RegistrationProcessRequest(BaseModel):
    candidate_id: int = Field(..., gt=0)
    exam_id: int = Field(..., gt=0)


class RegistrationProcessResponse(BaseModel):
    status: str
    job_id: int | None = None
    processed_questions: int = 0
    created_variants: int = 0
    skipped_questions: int = 0
    detail: str | None = None
