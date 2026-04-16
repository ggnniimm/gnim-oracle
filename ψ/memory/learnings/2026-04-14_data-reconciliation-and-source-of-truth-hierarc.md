---
title: ## Data Reconciliation and Source of Truth Hierarchy
tags: [data-quality, thai-legal-rag, oag, legal-documents, source-of-truth, rag]
created: 2026-04-14
source: Oracle Learn
---

# ## Data Reconciliation and Source of Truth Hierarchy

## Data Reconciliation and Source of Truth Hierarchy

### Context
OAG (สำนักงานอัยการสูงสุด) file reconciliation — Excel spreadsheet vs Drive folder vs md_backup.

### Pattern: Excel is Not Ground Truth for Legal Documents
Always cross-check Excel against domain expert before bulk operations. Typical Excel errors found:
- Typos (3/2563 was actually 7/2563)
- Wrong years (2562 vs 2552)
- Duplicates (same ruling uploaded twice with different year labels)

Only domain expert (Ming) could identify these by knowing original documents.

### Pattern: Show List Before Bulk Delete
For bulk deletions from a corpus:
1. Show the list with counts first
2. Flag outliers (e.g., year 2552 when everything else is 2562+)
3. Get confirmation on ambiguous cases
4. THEN delete

OCR cache as safety net — even when md_backup files are deleted, cached OCR preserves content. Multiple data layers = multiple recovery options.

### Pattern: Retry-File Pattern for Surgical Batch Processing
Instead of reprocessing entire folders, create a targeted file ID list. Process only the files you need:
```bash
python3 batch_index.py --retry-file missing_files.txt
```
28 files in 4 min vs 554 files in 45+ min.

### Pattern: Thai Legal Document Structure Matters
ข้อเท็จจริง (background facts) vs ข้อวินิจฉัย (actual ruling) carry different legal weight. Never cite ข้อเท็จจริง as if it were the ruling's conclusion. AI-generated OCR summaries can bake in interpretive errors from background narrative into the ruling summary — this propagates through RAG as false authoritative text.

---
*Added via Oracle Learn*
