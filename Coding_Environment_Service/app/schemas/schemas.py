from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


# ── Auth ──────────────────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str
    exam_id: str
    client_info: Optional[Dict[str, Any]] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    session_id: str
    expires_in: int


# ── Questions ─────────────────────────────────────────────────────────────────
class TestCase(BaseModel):
    id: str
    input: str = ""
    function_name: Optional[str] = None
    function_args: Optional[List[Any]] = None
    function_kwargs: Optional[Dict[str, Any]] = None
    expected_output_json: Optional[Any] = None
    expected_output: str
    is_sample: bool = False          # sample cases shown to candidate
    time_limit_ms: Optional[int] = None
    memory_limit_mb: Optional[int] = None


class Question(BaseModel):
    id: str
    title: str
    description: str
    constraints: Optional[str] = None
    examples: List[Dict[str, str]] = []
    test_cases: List[TestCase] = []
    supported_languages: List[str] = []
    starter_code: Dict[str, str] = {}
    difficulty: str = "medium"
    tags: List[str] = []


class QuestionPublic(BaseModel):
    """What the candidate sees — no hidden test case expected outputs."""
    id: str
    title: str
    description: str
    constraints: Optional[str] = None
    examples: List[Dict[str, str]] = []
    sample_test_cases: List[TestCase] = []   # only is_sample=True cases
    supported_languages: List[str] = []
    starter_code: Dict[str, str] = {}
    difficulty: str


# ── Submissions ───────────────────────────────────────────────────────────────
class SubmissionRequest(BaseModel):
    question_id: str
    language: str
    source_code: str = Field(..., max_length=65536)
    session_id: Optional[str] = None

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        allowed = {"python", "javascript", "java", "cpp", "go", "rust"}
        if v.lower() not in allowed:
            raise ValueError(f"Language must be one of {allowed}")
        return v.lower()


class TestCaseResult(BaseModel):
    test_case_id: str
    passed: bool
    actual_output: Optional[str] = None
    expected_output: Optional[str] = None  # only for sample cases
    execution_time_ms: Optional[int] = None
    memory_used_kb: Optional[int] = None
    error: Optional[str] = None


class SubmissionResponse(BaseModel):
    submission_id: str
    status: str
    message: str = "Submission queued for execution"


class SubmissionResult(BaseModel):
    submission_id: str
    question_id: str
    language: str
    status: str
    passed_count: int
    total_count: int
    test_results: List[TestCaseResult]
    execution_time_ms: Optional[int] = None
    memory_used_kb: Optional[int] = None
    error_message: Optional[str] = None
    submitted_at: datetime
    completed_at: Optional[datetime] = None


# ── Execution (run without submitting) ───────────────────────────────────────
class RunRequest(BaseModel):
    question_id: Optional[Any] = None
    language: str
    source_code: str = Field(..., max_length=65536)
    stdin: str = Field(default="", max_length=1048576)

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        aliases = {
            "py": "python",
            "python3": "python",
            "js": "javascript",
            "node": "javascript",
            "c++": "cpp",
            "cxx": "cpp",
            "golang": "go",
        }
        normalized = aliases.get((v or "").strip().lower(), (v or "").strip().lower())
        allowed = {"python", "javascript", "java", "cpp", "go", "rust"}
        if normalized not in allowed:
            raise ValueError(f"Language must be one of {allowed}")
        return normalized


class RunResult(BaseModel):
    stdout: str
    stderr: str
    exit_code: int
    execution_time_ms: int
    memory_used_kb: Optional[int] = None
    timed_out: bool = False


# ── Proctoring ────────────────────────────────────────────────────────────────
class ProctoringEvent(BaseModel):
    event_type: str   # tab_switch | copy_attempt | paste_attempt | window_blur | fullscreen_exit
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


class ClientLogRequest(BaseModel):
    event_type: str
    session_id: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
