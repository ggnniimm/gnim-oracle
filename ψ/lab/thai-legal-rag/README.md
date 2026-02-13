# Thai Legal RAG v2

> Clean architecture for Thai government legal document Q&A.

Lessons from `thai-rag-poc` (700+ documents, FAISS + LightRAG + Gemini) applied to a clean codebase.

## Quick Start

```bash
# 1. Install
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Edit .env with your API keys and folder IDs

# 3. Index a Drive folder
python pipeline/batch_index.py \
  --folder-id YOUR_DRIVE_FOLDER_ID \
  --category กรมบัญชีกลาง

# 4. Query via UI
streamlit run app/streamlit_app.py

# 5. Run tests
pytest tests/
```

## Architecture

```
src/
├── ingestion/      # Drive → OCR → Chunks → Dedup
├── indexing/       # FAISS + LightRAG (unified IndexManager)
├── retrieval/      # Query expand → parallel search → rerank
├── generation/     # Gemini Flash + legal persona
└── config.py       # All settings from env vars
```

## Key Design Decisions

| Decision | Reason |
|----------|--------|
| Gemini Vision OCR | Better than Tesseract for Thai government scan PDFs |
| Fusion retrieval (auto) | User doesn't choose FAISS vs LightRAG — both are queried, results merged |
| SQLite dedup | Lightweight, prevents re-indexing across runs |
| Config from env only | No hardcoded paths, runs anywhere |
| Failed log file | Retry failed files without re-indexing everything |

## Environment Variables

See `.env.example` for all required variables.

| Variable | Description |
|----------|-------------|
| `GEMINI_API_KEYS` | Comma-separated Gemini API keys (rotation) |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Service account JSON string or file path |
| `DRIVE_FOLDER_CGD` | Google Drive folder ID for กรมบัญชีกลาง |
| `DRIVE_FOLDER_ADMIN_COURT` | Google Drive folder ID for ศาลปกครอง |
| `DRIVE_FOLDER_AG` | Google Drive folder ID for สำนักงานอัยการสูงสุด |
| `THAI_RAG_DATA_DIR` | Local data directory (default: `/tmp/thai-legal-rag`) |

## Batch Indexer

```bash
# Index all PDFs in a folder
python pipeline/batch_index.py --folder-id FOLDER_ID --category กรมบัญชีกลาง

# Dry run (list files only)
python pipeline/batch_index.py --folder-id FOLDER_ID --category กรมบัญชีกลาง --dry-run

# Retry failed files
python pipeline/batch_index.py --folder-id FOLDER_ID --category กรมบัญชีกลาง \
  --retry-file /tmp/thai-legal-rag/failed_logs/failed_20260213_120000.txt

# FAISS only (skip LightRAG, faster)
python pipeline/batch_index.py --folder-id FOLDER_ID --category กรมบัญชีกลาง --no-lightrag
```

## Tests

```bash
pytest tests/test_chunker.py          # No API key needed
pytest tests/test_retrieval.py        # Partial (reranker tests need no API key)
pytest tests/test_ocr.py              # Needs GEMINI_API_KEYS
```
