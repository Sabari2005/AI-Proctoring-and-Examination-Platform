import os
from pathlib import Path
from dotenv import load_dotenv

CURRENT_ENV = Path(__file__).resolve().parents[1] / ".env"
ROOT_ENV = Path(__file__).resolve().parents[3] / ".env"

load_dotenv(CURRENT_ENV)
load_dotenv(ROOT_ENV)


class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "").strip()
    INTERNAL_TOKEN: str = os.getenv("MORPHING_SERVICE_TOKEN", "").strip()

    def validate(self) -> None:
        if not self.DATABASE_URL:
            raise EnvironmentError("DATABASE_URL is required for llm_morphing server")


settings = Settings()
