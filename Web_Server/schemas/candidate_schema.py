from pydantic import BaseModel
from typing import List, Optional
from typing import Any


class AccountUpdate(BaseModel):
    candidate_id: int
    mobile_no: str
    country: str
    timezone: str


class ProfileUpdate(BaseModel):
    candidate_id: int
    education_level: str
    university: str
    specialization: str
    graduation_year: int
    years_of_experience: int
    skills: List[str]


class LinksUpdate(BaseModel):
    candidate_id: int
    linkedin: str
    github: str
    website: Optional[str]


class OnboardingStepUpdate(BaseModel):
    candidate_id: int
    step: int


class DashboardProfileUpdate(BaseModel):
    candidate_id: int
    full_name: str
    email: str
    mobile_no: str


class AttemptAnswerItem(BaseModel):
    question_id: int
    answer: Any


class SubmitAttemptAnswersRequest(BaseModel):
    answers: List[AttemptAnswerItem]