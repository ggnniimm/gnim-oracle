# Lesson: Thai Legal RAG — Drive Shared Folders + Batch Index Quality Audit

**Date**: 2026-02-23
**Source**: cgd2-batch-index session

## Pattern 1: Drive API — Shared Folder Access

`list_files()` in `drive.py` will silently return 0 files for shared folders unless both flags are set:

```python
service.files().list(
    q=f"'{folder_id}' in parents and trashed = false",
    supportsAllDrives=True,           # REQUIRED for shared drives
    includeItemsFromAllDrives=True,   # REQUIRED for items from all drives
    ...
)
```

Without these flags: folder metadata is accessible (`files().get()` works), but listing returns empty. No error — just 0 files.

## Pattern 2: OCR Cache File Structure

The cache file at `data/ocr_cache/<sha256_prefix>.json` has these top-level keys:
```
{text, doc_type, category, confidence, file_id, filename}
```

Metadata fields (ref_number, date, title, doc_number) are **inside** the `text` field as YAML frontmatter, NOT as top-level keys. Always parse frontmatter from `text` to check metadata completeness.

## Pattern 3: dedup.db Schema

```sql
CREATE TABLE indexed_chunks (
    hash TEXT,
    source_id TEXT,
    added_at TEXT
)
```

Table name is `indexed_chunks` (not `indexed`). To remove entries for re-indexing:
```python
conn.execute("DELETE FROM indexed_chunks WHERE source_id IN (?)", [file_id])
```

## Pattern 4: Re-Index Pipeline (3 stores)

When re-indexing files with bad metadata, must clean 3 stores:
1. **FAISS metadata.pkl** — filter out chunks by `source_drive_id`
2. **BM25 bm25.pkl** — filter corpus + metadata in parallel
3. **dedup.db indexed_chunks** — delete by `source_id`

Then delete OCR cache to force re-OCR, create retry file, run batch_index.

Note: FAISS has no delete API — bad chunks removed from metadata.pkl but vectors remain in FAISS index. They score poorly (empty metadata) but still consume vector slots. Fix: periodic rebuild.

## Pattern 5: Category Granularity for กวจ. Documents

Three meaningful categories for กวจ. documents:
- `ข้อหารือ กวจ.` — case-by-case rulings (majority)
- `ข้อหารือแนวทางปฏิบัติ กวจ.` — inquiries about guidelines (title contains "แนวทางปฏิบัติ")
- `ซ้อมความเข้าใจ กวจ.` — authoritative circulars (title contains "ซ้อมความเข้าใจ")

Detection logic from MD backup title field:
```python
if 'ซ้อมความเข้าใจ' in title or 'ซักซ้อม' in title:
    category = 'ซ้อมความเข้าใจ กวจ.'
elif 'แนวทางปฏิบัติ' in title:
    category = 'ข้อหารือแนวทางปฏิบัติ กวจ.'
```

## Pattern 6: Large File Retry

Gemini File API sometimes fails for files >5 MB on first OCR attempt. Retry usually succeeds. `กวจ_ว48` at 9.3 MB failed once, succeeded on retry with no changes.
