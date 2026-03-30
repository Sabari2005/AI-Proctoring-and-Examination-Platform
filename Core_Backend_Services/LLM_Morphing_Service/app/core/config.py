import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", os.getenv("GEMINI_API_KEY", ""))

    DEFAULT_MODEL: str = os.getenv("DEFAULT_MODEL", "llama-3.3-70b-versatile")
    FALLBACK_MODEL: str = os.getenv("FALLBACK_MODEL", "gemini-1.5-flash")

    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    MIN_SEMANTIC_SCORE: float = float(os.getenv("MIN_SEMANTIC_SCORE", "0.82"))

    LANGCHAIN_TRACING_V2: str = os.getenv("LANGCHAIN_TRACING_V2", "false")
    LANGCHAIN_PROJECT: str = os.getenv("LANGCHAIN_PROJECT", "llm-question-morphing")

    # Sentence transformer model (runs locally, no API key needed)
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    def validate(self):
        missing = []
        if not self.GROQ_API_KEY:
            missing.append("GROQ_API_KEY")
        if missing:
            raise EnvironmentError(
                f"Missing required environment variables: {', '.join(missing)}\n"
                "Set the missing keys in .env and rerun."
            )


settings = Settings()