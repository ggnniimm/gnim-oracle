"""
Central Gemini client factory — every API call goes through here.
Default timeout on ALL calls to prevent silent hangs.
"""
import time
import random
import logging
import httpx
from google import genai

from src.config import (
    GEMINI_API_KEYS,
    GOOGLE_CLOUD_PROJECT,
    GOOGLE_CLOUD_LOCATION,
    OCR_LOCATION,
    USE_VERTEX_AI,
)

logger = logging.getLogger(__name__)

_KEY_INDEX = 0

# Default timeout for all Gemini API calls (ms)
DEFAULT_TIMEOUT_MS = 120_000  # 120 seconds

# Retry config for transient 503/429 errors
_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 2  # seconds — exponential: 2, 4, 8 + jitter
_FINAL_ROUND_COOLDOWN = 20  # seconds — wait after full chain fails once before last-chance round

# Fallback models when primary is overloaded.
# Different aliases often route to different backend capacity pools,
# so cycling through them gives a better shot at finding a healthy one.
_FALLBACK_MODELS = [
    "gemini-2.5-flash-lite",
    "gemini-flash-latest",
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
    if USE_VERTEX_AI:
        return genai.Client(
            vertexai=True,
            project=GOOGLE_CLOUD_PROJECT,
            location=GOOGLE_CLOUD_LOCATION,
            http_options={"timeout": DEFAULT_TIMEOUT_MS},
        )
    return genai.Client(
        api_key=_next_key(),
        http_options={"timeout": DEFAULT_TIMEOUT_MS},
    )


def get_ocr_client(timeout_ms: int = DEFAULT_TIMEOUT_MS) -> genai.Client:
    """Return a Gemini client pinned to OCR_LOCATION (us-central1).

    OCR extraction uses a separate Vertex AI location from the embedding client
    (which must be on 'global' for gemini-embedding-2). This gives OCR its own
    Pro quota pool and avoids quota cross-contamination.

    Pass a larger timeout_ms for non-streaming structure calls on large docs —
    the model may take several minutes to generate a full structured output for
    70+ page documents. We pass a custom httpx client because the SDK's
    http_options["timeout"] is not propagated to the underlying httpx layer.
    """
    if USE_VERTEX_AI:
        timeout_s = timeout_ms / 1000
        custom_httpx = httpx.Client(timeout=httpx.Timeout(timeout_s))
        return genai.Client(
            vertexai=True,
            project=GOOGLE_CLOUD_PROJECT,
            location=OCR_LOCATION,
            http_options={"timeout": timeout_ms, "httpx_client": custom_httpx},
        )
    return get_client()  # AI Studio: location doesn't apply


_TRANSIENT_MARKERS = (
    "503", "429", "500", "unavailable", "overloaded",
    "resource_exhausted", "timeout", "timed out", "stream idle",
    "deadline exceeded",
)


def _is_transient(exc: Exception) -> bool:
    return any(k in str(exc).lower() for k in _TRANSIENT_MARKERS)


def generate_with_retry(client: genai.Client, **kwargs):
    """Call client.models.generate_content with exponential backoff + jitter.

    Strategy:
      1. Try primary model up to _MAX_RETRIES with exp backoff.
      2. If still failing, cycle through fallback models (one attempt each).
      3. If the full chain fails, cooldown _FINAL_ROUND_COOLDOWN seconds and
         do one last round across all models. Google infra 503s typically
         recover within 30-60s.
      4. Non-transient errors (auth, invalid request) raise immediately.
    """
    primary_model = kwargs.get("model", "gemini-2.5-flash")
    models_to_try = [primary_model] + [m for m in _FALLBACK_MODELS if m != primary_model]
    last_exc = None

    # Round 1: try each model with its own retry budget
    for model in models_to_try:
        if model != primary_model:
            logger.warning(f"Primary model {primary_model} unavailable, falling back to {model}")
        kwargs["model"] = model
        for attempt in range(_MAX_RETRIES):
            try:
                return client.models.generate_content(**kwargs)
            except Exception as e:
                if not _is_transient(e):
                    raise
                last_exc = e
                if attempt + 1 < _MAX_RETRIES:
                    delay = _RETRY_BASE_DELAY * (2 ** attempt) + random.uniform(0, 1.5)
                    logger.warning(f"Gemini {model} attempt {attempt+1}/{_MAX_RETRIES}, retry in {delay:.1f}s")
                    time.sleep(delay)
                    client = get_client()

    # Round 2: full-chain cooldown + one last try per model
    logger.warning(
        f"All models failed round 1. Cooling down {_FINAL_ROUND_COOLDOWN}s before final attempt."
    )
    time.sleep(_FINAL_ROUND_COOLDOWN + random.uniform(0, 5))
    for model in models_to_try:
        kwargs["model"] = model
        try:
            client = get_client()
            return client.models.generate_content(**kwargs)
        except Exception as e:
            if not _is_transient(e):
                raise
            last_exc = e
            logger.warning(f"Gemini {model} final attempt failed: {str(e)[:100]}")

    raise last_exc
