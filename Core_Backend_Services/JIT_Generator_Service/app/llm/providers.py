from functools import lru_cache
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from app.core.config import settings


@lru_cache(maxsize=1)
def get_primary_llm():
    return ChatGroq(
        model=settings.DEFAULT_MODEL,
        api_key=settings.GROQ_API_KEY,
        temperature=0.8,       # slightly higher for varied question generation
        max_tokens=2048,
    )


@lru_cache(maxsize=1)
def get_fallback_llm():
    return ChatGoogleGenerativeAI(
        model=settings.FALLBACK_MODEL,
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=0.8,
        max_output_tokens=2048,
    )


def invoke_with_fallback(prompt_value) -> str:
    try:
        return get_primary_llm().invoke(prompt_value).content
    except Exception as e:
        print(f"[LLM] Groq failed ({e}), falling back to Gemini...")
        try:
            return get_fallback_llm().invoke(prompt_value).content
        except Exception as e2:
            raise RuntimeError(f"Both LLMs failed. Groq: {e} | Gemini: {e2}")