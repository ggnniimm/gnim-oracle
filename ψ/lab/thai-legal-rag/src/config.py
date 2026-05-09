"""
Central configuration — all settings from environment variables.
No hardcoded paths anywhere else in the codebase.
"""
import os
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(usecwd=True, raise_error_if_not_found=False))

# --- API Keys ---
GEMINI_API_KEYS: list[str] = [
    k.strip()
    for k in os.getenv("GEMINI_API_KEYS", os.getenv("GEMINI_API_KEY", "")).split(",")
    if k.strip()
]
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Vertex AI mode (uses ADC instead of API keys, billed through GCP project)
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "").strip()
GOOGLE_CLOUD_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1").strip()
USE_VERTEX_AI = bool(GOOGLE_CLOUD_PROJECT)

GOOGLE_DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]
# OAuth2 paths (set via env or use defaults)
# GOOGLE_CREDENTIALS_JSON and GOOGLE_TOKEN_JSON are read directly in drive.py

# --- Google Drive ---
DRIVE_FOLDER_IDS: dict[str, str] = {
    # category_name -> folder_id  (set via env: DRIVE_FOLDER_GVAJ, etc.)
    "ข้อหารือ กวจ.": os.getenv("DRIVE_FOLDER_GVAJ", ""),
    "กรมบัญชีกลาง": os.getenv("DRIVE_FOLDER_CGD", ""),
    "ศาลปกครอง": os.getenv("DRIVE_FOLDER_ADMIN_COURT", ""),
    "สำนักงานอัยการสูงสุด": os.getenv("DRIVE_FOLDER_AG", ""),
    "กฎหมาย": os.getenv("DRIVE_FOLDER_LAW", ""),
}

# --- Storage paths ---
BASE_DIR = Path(os.getenv("THAI_RAG_DATA_DIR", "/tmp/thai-legal-rag"))
BM25_DIR = BASE_DIR / "bm25_index"
QDRANT_URL = os.getenv("QDRANT_URL", "")  # e.g. http://localhost:6333 — if set, use server mode
QDRANT_PATH = BASE_DIR / "qdrant_store"  # used only when QDRANT_URL is not set
DEDUP_DB = BASE_DIR / "dedup.db"
OCR_CACHE_DIR = BASE_DIR / "ocr_cache"
MD_BACKUP_DIR = BASE_DIR / "md_backup"
FAILED_LOG_DIR = BASE_DIR / "failed_logs"

# Create dirs on import
for _d in [BM25_DIR, OCR_CACHE_DIR, MD_BACKUP_DIR, FAILED_LOG_DIR]:
    _d.mkdir(parents=True, exist_ok=True)

# --- Models ---
GEMINI_FLASH_MODEL = "gemini-2.5-flash"
GEMINI_PRO_MODEL = "gemini-2.5-pro"
# OCR_EXTRACT_MODEL: model used for the extract phase of OCR (verbatim doc body).
# classify + anchor stay on Flash (cheap, sufficient). Pro for extract = better
# table fidelity, fewer dropped sections, thinking-mode reasoning on schema.
OCR_EXTRACT_MODEL = os.getenv("OCR_EXTRACT_MODEL", GEMINI_PRO_MODEL)
GEMINI_EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "gemini-embedding-2-preview")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "3072"))
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "thai_legal_rag")

# --- Chunking ---
CHUNK_SIZE = 400       # tokens / chars
CHUNK_OVERLAP = 100

# --- Retrieval ---
VECTOR_TOP_K = 80
BM25_TOP_K = 40
BM25_WEIGHT = 0.9  # keyword match nearly equals semantic — high recall
RERANK_TOP_K = 15
MMR_LAMBDA = 0.7   # 1.0 = pure relevance, 0.0 = pure diversity
MMR_INJECT_EXTRAS = 4  # after MMR, inject this many extra chunks per retrieved source
ORIGINAL_QUERY_BOOST = 1.3  # boost scores from the original query vs expanded queries
RECENCY_BOOST = 0.05  # newer docs get up to +5% score boost (tiebreaker only)

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
