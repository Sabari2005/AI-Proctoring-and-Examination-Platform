"""
question_store.py — Loads and caches questions from JSON files.
JSON schema matches the Question pydantic model.
"""
import json
from pathlib import Path
from typing import Dict, Optional
import structlog

from app.schemas.schemas import Question, QuestionPublic

log = structlog.get_logger()

QUESTIONS_DIR = Path(__file__).parent.parent.parent / "questions"


class QuestionStore:
    def __init__(self):
        self._cache: Dict[str, Question] = {}
        self._load_all()

    def _load_all(self):
        if not QUESTIONS_DIR.exists():
            log.warning("questions_dir_not_found", path=str(QUESTIONS_DIR))
            return
        for f in QUESTIONS_DIR.glob("*.json"):
            if f.name == "schema.json":
                continue
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                q = Question(**data)
                self._cache[q.id] = q
                log.info("question_loaded", id=q.id, title=q.title)
            except Exception as e:
                log.error("question_load_error", file=str(f), error=str(e))
        log.info("question_store_ready", count=len(self._cache))

    def get(self, question_id: str) -> Optional[Question]:
        return self._cache.get(question_id)

    def get_public(self, question_id: str) -> Optional[QuestionPublic]:
        q = self._cache.get(question_id)
        if not q:
            return None
        return QuestionPublic(
            id=q.id,
            title=q.title,
            description=q.description,
            constraints=q.constraints,
            examples=q.examples,
            sample_test_cases=[tc for tc in q.test_cases if tc.is_sample],
            supported_languages=q.supported_languages,
            starter_code=q.starter_code,
            difficulty=q.difficulty,
        )

    def list_ids(self):
        return list(self._cache.keys())

    def reload(self):
        self._cache.clear()
        self._load_all()


question_store = QuestionStore()
