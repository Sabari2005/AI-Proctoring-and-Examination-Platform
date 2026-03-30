import os
from dotenv import load_dotenv
load_dotenv()


class Settings:
    GROQ_API_KEY:   str   = os.getenv("GROQ_API_KEY", "")
    GOOGLE_API_KEY: str   = os.getenv("GOOGLE_API_KEY", os.getenv("GEMINI_API_KEY", ""))
    DEFAULT_MODEL:  str   = os.getenv("DEFAULT_MODEL", "llama-3.3-70b-versatile")
    FALLBACK_MODEL: str   = os.getenv("FALLBACK_MODEL", "gemini-1.5-flash")

    # Adaptive engine tuning
    LEARNING_RATE:       float = float(os.getenv("JIT_LEARNING_RATE", "0.4"))
    MAX_DIFFICULTY_JUMP: int   = int(os.getenv("JIT_MAX_DIFF_JUMP", "2"))
    STREAK_THRESHOLD:    int   = int(os.getenv("JIT_STREAK_THRESHOLD", "3"))
    LOCK_AFTER_WRONG:    int   = int(os.getenv("JIT_LOCK_AFTER_WRONG", "3"))

    # Default expected times per question type (seconds)
    EXPECTED_TIMES: dict = {
        "mcq":       60,
        "fib":       45,
        "short":    120,
        "msq":       90,
        "numerical": 90,
        "long":     480,
        "coding":   900,
    }

    def validate(self):
        missing = []
        if not self.GROQ_API_KEY:  missing.append("GROQ_API_KEY")
        if missing:
            raise EnvironmentError(
                f"Missing env vars: {', '.join(missing)}. Copy .env.example → .env"
            )


settings = Settings()