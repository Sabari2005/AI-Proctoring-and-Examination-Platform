from fastapi import APIRouter, Depends, HTTPException
from app.routers.auth import get_current_user
from app.services.question_store import question_store
from app.schemas.schemas import QuestionPublic

router = APIRouter()


@router.get("/{question_id}", response_model=QuestionPublic)
async def get_question(question_id: str, current_user=Depends(get_current_user)):
    q = question_store.get_public(question_id)
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    return q


@router.get("/")
async def list_questions(current_user=Depends(get_current_user)):
    return [
        question_store.get_public(qid)
        for qid in question_store.list_ids()
    ]
