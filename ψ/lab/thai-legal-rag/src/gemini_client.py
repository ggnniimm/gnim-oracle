"""
Central Gemini client factory — every API call goes through here.
Default timeout on ALL calls to prevent silent hangs.
"""
from google import genai

from src.config import GEMINI_API_KEYS

_KEY_INDEX = 0

# Default timeout for all Gemini API calls (ms)
DEFAULT_TIMEOUT_MS = 120_000  # 120 seconds


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
