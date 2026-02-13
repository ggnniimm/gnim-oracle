"""
Central configuration — all settings from environment variables.
No hardcoded paths anywhere else in the codebase.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# --- API Keys ---
GEMINI_API_KEYS: list[str] = [
    k.strip()
    for k in os.getenv("GEMINI_API_KEYS", os.getenv("GEMINI_API_KEY", "")).split(",")
    if k.strip()
]

GOOGLE_SERVICE_ACCOUNT_JSON: str = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
# Either a JSON string or a file path
GOOGLE_DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# --- Google Drive ---
DRIVE_FOLDER_IDS: dict[str, str] = {
    # category_name -> folder_id  (set via env: DRIVE_FOLDER_CGD, etc.)
    "กรมบัญชีกลาง": os.getenv("DRIVE_FOLDER_CGD", ""),
    "ศาลปกครอง": os.getenv("DRIVE_FOLDER_ADMIN_COURT", ""),
    "สำนักงานอัยการสูงสุด": os.getenv("DRIVE_FOLDER_AG", ""),
}

# --- Storage paths ---
BASE_DIR = Path(os.getenv("THAI_RAG_DATA_DIR", "/tmp/thai-legal-rag"))
FAISS_DIR = BASE_DIR / "faiss_index"
LIGHTRAG_DIR = BASE_DIR / "lightrag_index"
DEDUP_DB = BASE_DIR / "dedup.db"
OCR_CACHE_DIR = BASE_DIR / "ocr_cache"
FAILED_LOG_DIR = BASE_DIR / "failed_logs"

# Create dirs on import
for _d in [FAISS_DIR, LIGHTRAG_DIR, OCR_CACHE_DIR, FAILED_LOG_DIR]:
    _d.mkdir(parents=True, exist_ok=True)

# --- Models ---
GEMINI_FLASH_MODEL = "gemini-2.0-flash"
GEMINI_EMBEDDING_MODEL = "models/text-embedding-004"
EMBEDDING_DIM = 768  # text-embedding-004 default output dim

# --- Chunking ---
CHUNK_SIZE = 400       # tokens / chars
CHUNK_OVERLAP = 100

# --- Retrieval ---
FAISS_TOP_K = 10
LIGHTRAG_TOP_K = 10
RERANK_TOP_K = 5

# --- OCR ---
OCR_MIN_CHARS_PER_PAGE = 50   # pages with fewer chars will be force-OCR'd
OCR_MAX_PAGES_PER_BATCH = 20  # send at most N pages per Gemini call

# --- Rate limiting ---
GEMINI_REQUESTS_PER_MINUTE = 60
EMBEDDING_REQUESTS_PER_MINUTE = 1500

def get_drive_folder_id(category: str) -> str:
    """Return folder ID for a category, raise if not configured."""
    fid = DRIVE_FOLDER_IDS.get(category, "")
    if not fid:
        # also try env var directly
        fid = os.getenv(f"DRIVE_FOLDER_{category.upper()}", "")
    if not fid:
        raise ValueError(
            f"Drive folder ID for '{category}' not configured. "
            f"Set DRIVE_FOLDER_CGD / DRIVE_FOLDER_ADMIN_COURT / etc."
        )
    return fid
