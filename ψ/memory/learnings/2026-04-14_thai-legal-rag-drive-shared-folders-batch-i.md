---
title: ## Thai Legal RAG — Drive Shared Folders + Batch Index Quality
tags: [google-drive, batch-index, dedup, thai-legal, gemini]
created: 2026-04-14
source: cgd2-batch-index session 2026-02-23
---

# ## Thai Legal RAG — Drive Shared Folders + Batch Index Quality

## Thai Legal RAG — Drive Shared Folders + Batch Index Quality

1. **Drive API shared folder access**: `list_files()` silently returns 0 for shared folders unless both `supportsAllDrives=True` AND `includeItemsFromAllDrives=True` flags are set. No error — just 0 files.

2. **OCR cache structure**: `data/ocr_cache/<sha256_prefix>.json` has `{text, doc_type, category, confidence, file_id, filename}`. Metadata fields (ref_number, date, title) are INSIDE `text` as YAML frontmatter — NOT top-level keys.

3. **dedup.db schema**: Table name is `indexed_chunks` (not `indexed`). `DELETE FROM indexed_chunks WHERE source_id IN (?)` to remove for re-indexing.

4. **Re-index requires cleaning 3 stores**: FAISS metadata.pkl + BM25 bm25.pkl + dedup.db indexed_chunks.

5. **กวจ document categories**: `ข้อหารือ กวจ.` (majority), `ข้อหารือแนวทางปฏิบัติ กวจ.` (title has "แนวทางปฏิบัติ"), `ซ้อมความเข้าใจ กวจ.` (title has "ซ้อมความเข้าใจ").

6. **Gemini File API**: May fail for files >5 MB on first attempt. Retry usually succeeds.

---
*Added via Oracle Learn*
