import os
from functools import lru_cache
from langchain_core.language_models import BaseChatModel
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from app.core.config import settings


@lru_cache(maxsize=1)
def get_primary_llm() -> BaseChatModel:
    """
    Primary LLM: Groq (llama-3.3-70b-versatile)
    Fast, free tier, ~300 tok/s — used for all morph nodes.
    """
    return ChatGroq(
        model=settings.DEFAULT_MODEL,
        api_key=settings.GROQ_API_KEY,
        temperature=0.7,
        max_tokens=1024,
    )


@lru_cache(maxsize=1)
def get_fallback_llm() -> BaseChatModel:
    """
    Fallback LLM: Gemini 1.5 Flash
    Used when Groq hits rate limits or returns an error.
    """
    return ChatGoogleGenerativeAI(
        model=settings.FALLBACK_MODEL,
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=0.7,
        max_output_tokens=1024,
    )


def get_llm(use_fallback: bool = False) -> BaseChatModel:
    """Return primary or fallback LLM."""
    if use_fallback:
        return get_fallback_llm()
    return get_primary_llm()


def invoke_with_fallback(prompt_value, max_retries: int = 1) -> str:
    """
    Invoke primary LLM. On any exception, automatically fall back to Gemini.
    Returns the text content as a plain string.
    """
    try:
        result = get_primary_llm().invoke(prompt_value)
        return result.content
    except Exception as primary_error:
        if not settings.GOOGLE_API_KEY:
            raise RuntimeError(
                f"Groq failed and Gemini fallback is not configured.\n"
                f"  Groq error: {primary_error}\n"
                "Set GOOGLE_API_KEY or GEMINI_API_KEY to enable fallback."
            )
        print(f"[LLM] Groq failed ({primary_error}), switching to Gemini fallback...")
        try:
            result = get_fallback_llm().invoke(prompt_value)
            return result.content
        except Exception as fallback_error:
            raise RuntimeError(
                f"Both LLMs failed.\n"
                f"  Groq error:   {primary_error}\n"
                f"  Gemini error: {fallback_error}"
            )