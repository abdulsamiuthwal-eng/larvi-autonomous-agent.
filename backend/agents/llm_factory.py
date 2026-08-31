"""
Larvi — Resilient LLM Factory
Provides multi-model automatic fallback cascade across Gemini models
to eliminate 429 quota errors and guarantee continuous availability.

Key design:
  - max_retries=1 on every LLM instance → prevents LangChain's internal
    exponential backoff (default 6 retries = up to 126 seconds of waiting).
    Our own factory cascade then instantly tries the next model instead.
"""
import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from config import settings

logger = logging.getLogger(__name__)

# Production model cascade — only models confirmed working on new API keys.
# Removed: gemini-2.5-flash (404), gemini-1.5-flash-8b (404)
FALLBACK_CASCADE = [
    "gemini-2.5-flash-lite",   # Primary: 1500 RPD free tier
    "gemini-2.0-flash",        # Fallback 1: v2 stable, widely available
    "gemini-1.5-flash",        # Fallback 2: proven v1 stable model
    "gemini-3.6-flash",        # Fallback 3: Google-recommended for new API keys
]

# Remove duplicates while preserving order
_SEEN = set()
ORDERED_MODELS = [m for m in FALLBACK_CASCADE if not (m in _SEEN or _SEEN.add(m))]


def get_llm(temperature: float = 0.1, model: str = None) -> ChatGoogleGenerativeAI:
    """
    Create a ChatGoogleGenerativeAI instance with max_retries=1.

    Setting max_retries=1 is critical: LangChain's default is 6 retries with
    exponential backoff (2+4+8+16+32+64 = 126 seconds total wait). With
    max_retries=1, LangChain gives up after a single 2-second retry, and our
    invoke_llm_with_fallback immediately switches to the next model instead.
    """
    chosen_model = model or ORDERED_MODELS[0]
    return ChatGoogleGenerativeAI(
        model=chosen_model,
        google_api_key=settings.GEMINI_API_KEY,
        temperature=temperature,
        max_retries=1,        # ← Critical: prevents 126-second backoff delays
    )


def invoke_llm_with_fallback(llm_invoker_fn, *args, **kwargs):
    """
    Invoke an LLM function with automatic model fallback.
    Catches both 429 quota errors AND 404 model-not-available errors.
    """
    last_error = None
    for model_name in ORDERED_MODELS:
        try:
            return llm_invoker_fn(model_name, *args, **kwargs)
        except Exception as e:
            err_str = str(e)
            is_quota   = "429" in err_str or "quota" in err_str.lower() or "resourceexhausted" in err_str.lower()
            is_no_model = "404" in err_str or "no longer available" in err_str.lower() or "not found" in err_str.lower()
            if is_quota or is_no_model:
                reason = "quota limit" if is_quota else "model unavailable (404)"
                logger.warning(f"[LLM Factory] '{model_name}' skipped ({reason}). Trying next...")
                last_error = e
                continue
            else:
                raise e

    # All models exhausted — raise last error
    if last_error:
        raise last_error

