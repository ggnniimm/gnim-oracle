"""
Central Gemini client factory — every API call goes through here.
Default timeout on ALL calls to prevent silent hangs.
"""
import time
import random
import logging
from google import genai

from src.config import GEMINI_API_KEYS

logger = logging.getLogger(__name__)

_KEY_INDEX = 0

# Default timeout for all Gemini API calls (ms)
DEFAULT_TIMEOUT_MS = 120_000  # 120 seconds

# Retry config for transient 503/429 errors
_MAX_RETRIES = 4
_RETRY_BASE_DELAY = 1  # seconds — exponential: 1, 2, 4, 8 + jitter

# Fallback models when primary is overloaded
_FALLBACK_MODELS = [
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash-lite",
]


def _next_key() -> str:
    global _KEY_INDEX
    if not GEMINI_API_KEYS:
        raise ValueError("No GEMINI_API_KEYS configured.")
    key = GEMINI_API_KEYS[_KEY_INDEX % len(GEMINI_API_KEYS)]
    _KEY_INDEX += 1
    return key


def get_client() -> genai.Client:
    """Return a Gemini client with default timeout baked in."""
    return genai.Client(
        api_key=_next_key(),
        http_options={"timeout": DEFAULT_TIMEOUT_MS},
    )


def generate_with_retry(client: genai.Client, **kwargs):
    """Call client.models.generate_content with exponential backoff + jitter.
    Falls back to lighter models if primary is persistently overloaded.
    """
    primary_model = kwargs.get("model", "gemini-2.5-flash")
    models_to_try = [primary_model] + _FALLBACK_MODELS
    last_exc = None

    for model in models_to_try:
        if model != primary_model:
            logger.warning(f"Primary model {primary_model} unavailable, falling back to {model}")
        kwargs["model"] = model
        for attempt in range(_MAX_RETRIES):
            try:
                return client.models.generate_content(**kwargs)
            except Exception as e:
                err_str = str(e)
                err_lower = err_str.lower()
                if any(k in err_lower for k in ("503", "429", "unavailable", "resource_exhausted", "timeout", "timed out", "stream idle")):
                    last_exc = e
                    if attempt + 1 < _MAX_RETRIES:
                        delay = _RETRY_BASE_DELAY * (2 ** attempt) + random.uniform(0, 1)
                        logger.warning(f"Gemini {model} attempt {attempt+1}/{_MAX_RETRIES}, retry in {delay:.1f}s")
                        time.sleep(delay)
                        client = get_client()
                else:
                    raise
    raise last_exc
