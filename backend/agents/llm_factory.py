"""
Larvi — Resilient LLM Factory
Provides multi-model automatic fallback cascade across Gemini models
to eliminate 429 quota errors and guarantee continuous availability.
"""
import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from config import settings

logger = logging.getLogger(__name__)

# Confirmed available models prioritizing high-quota production tiers
FALLBACK_CASCADE = [
    "gemini-2.5-flash-lite",   # high quota free tier (1500 RPD)
    "gemini-flash-lite-latest",
    "gemini-flash-latest",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.7-flash",
    "gemini-3.1-flash-lite",
]
# Remove duplicates while preserving order
_SEEN = set()
ORDERED_MODELS = [m for m in FALLBACK_CASCADE if not (m in _SEEN or _SEEN.add(m))]


def get_llm(temperature: float = 0.1, model: str = None) -> ChatGoogleGenerativeAI:
    """Create a ChatGoogleGenerativeAI instance."""
    chosen_model = model or ORDERED_MODELS[0]
    return ChatGoogleGenerativeAI(
        model=chosen_model,
        google_api_key=settings.GEMINI_API_KEY,
        temperature=temperature,
    )


def invoke_llm_with_fallback(llm_invoker_fn, *args, **kwargs):
    """
    Invoke an LLM function (e.g. llm.invoke or agent_executor.invoke).
    If a 429 / Quota / ResourceExhausted error occurs, automatically
    retries with the next model in the fallback cascade.
    """
    last_error = None
    for model_name in ORDERED_MODELS:
        try:
            return llm_invoker_fn(model_name, *args, **kwargs)
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "quota" in err_str.lower() or "resourceexhausted" in err_str.lower():
                logger.warning(f"[LLM Factory] Model '{model_name}' hit rate limit. Auto-falling back to next model...")
                last_error = e
                continue
            else:
                raise e

    # If all models failed, raise the last error
    if last_error:
        raise last_error
