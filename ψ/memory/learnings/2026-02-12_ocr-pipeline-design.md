# Lesson: OCR Batch Pipeline Design

**Date**: 2026-02-12
**Source**: Thai Legal RAG Pipeline implementation

## Core Lessons

### 1. Resume logic is non-negotiable for batch jobs
Build skip-already-processed logic before anything else. Pattern: log each success to a CSV immediately after it happens (not at the end). On restart, read the log and skip completed items. Cost: ~10 lines. Value: saves hours when network drops at file 350/700.

```python
# Append to log immediately after success
with open(log_path, 'a') as f:
    writer.writerow({"drive_id": id, "status": "ok", ...})
```

### 2. Gemini inline_data for PDFs (no upload lifecycle)
For PDFs ≤ a few MB, base64 inline_data is simpler than file upload API:

```python
pdf_b64 = base64.b64encode(pdf_bytes).decode('utf-8')
response = model.generate_content([
    prompt,
    {"inline_data": {"mime_type": "application/pdf", "data": pdf_b64}},
    "instruction"
])
```

No need to manage `model.upload_file()` lifecycle, expiry, or deletion.

### 3. Structured output embedded in freeform = fragile
Asking Gemini to return JSON at the end of freeform markdown works but breaks if:
- Gemini adds text after the JSON block
- JSON is malformed
- Regex pattern misses edge cases

Better for production: use `generation_config={"response_mime_type": "application/json", "response_schema": {...}}` for the metadata extraction step. Two-call approach (OCR first, extract second) is more reliable than one-call hybrid.

### 4. Google Drive public URL download
- Direct URL: `https://drive.google.com/uc?export=download&id=FILE_ID`
- Works for "anyone with link" public files
- Large files (>~25MB) need confirmation token from cookie flow
- For private/organizational files: use Drive API + service account
- Check first 4 bytes == `b'%PDF'` to verify actual PDF received

### 5. YAML frontmatter schema for RAG documents
Key fields for Thai legal RAG:
- `doc_type`, `issued_by`, `doc_number` — for metadata filtering
- `date_be`, `laws_referenced`, `sections_referenced` — for temporal and cross-reference filtering
- `source_drive` — provenance/traceability
- `quality: good|review-needed|low` — human review routing
- `status: active|amended|repealed` — for temporal RAG filtering

## Anti-patterns Avoided

- ❌ All-at-end logging (loses progress on failure)
- ❌ Two Gemini calls per file (doubles cost on free tier)
- ❌ Assuming Drive URL structure is stable (used detection not assumptions)
- ❌ Over-engineering validation before testing with real data

## Tags
`ocr`, `batch-pipeline`, `gemini`, `google-drive`, `rag`, `thai-legal`, `metadata`
