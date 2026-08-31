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

# Production model cascade — fastest & highest-quota first.
# All are Gemini Flash-class: low latency, high RPD, free tier friendly.
FALLBACK_CASCADE = [
    "gemini-2.5-flash-lite",   # Primary: 1500 RPD free tier, lowest latency
    "gemini-2.5-flash",        # Fallback 1: higher intelligence, still fast
    "gemini-1.5-flash",        # Fallback 2: stable v1 model
    "gemini-2.0-flash",        # Fallback 3: v2 stable release
    "gemini-1.5-flash-8b",     # Fallback 4: smallest/fastest emergency model
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
    Invoke an LLM function (e.g. llm.invoke or agent_executor.invoke).
    If a 429 / Quota / ResourceExhausted error occurs, automatically
    retries with the next model in the fallback cascade.

    With max_retries=1, each model attempt costs at most ~2 seconds before
    this cascade moves to the next model — giving sub-5-second total latency
    even when the primary model is exhausted.
    """
    last_error = None
    for model_name in ORDERED_MODELS:
        try:
            return llm_invoker_fn(model_name, *args, **kwargs)
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "quota" in err_str.lower() or "resourceexhausted" in err_str.lower():
                logger.warning(f"[LLM Factory] Model '{model_name}' hit rate limit. Instantly switching to next model...")
                last_error = e
                continue
            else:
                raise e

    # All models exhausted — raise last quota error
    if last_error:
        raise last_error
