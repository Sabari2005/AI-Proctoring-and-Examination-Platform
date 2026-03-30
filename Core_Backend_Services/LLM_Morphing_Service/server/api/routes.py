from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from server.config import settings
from server.db import get_db
from server.schemas import RegistrationProcessRequest, RegistrationProcessResponse
from server.services.registration_processor import process_registration

router = APIRouter(prefix="/internal/v1", tags=["registration-processing"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "llm_morphing_registration_server"}


@router.post("/registrations/process", response_model=RegistrationProcessResponse)
async def process_registration_request(
    payload: RegistrationProcessRequest,
    db: Session = Depends(get_db),
    x_internal_token: str | None = Header(default=None),
):
    configured_token = settings.INTERNAL_TOKEN
    if configured_token:
        if not x_internal_token or x_internal_token != configured_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid internal token",
            )

    result = await process_registration(
        candidate_id=payload.candidate_id,
        exam_id=payload.exam_id,
        db=db,
    )

    return RegistrationProcessResponse(**result)
