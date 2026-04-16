---
title: ## OAG Batch Indexing: Pipeline Reliability Lessons
tags: [pipeline, rag, gemini, indexing, reliability, thai-legal-rag, oag]
created: 2026-04-14
source: Oracle Learn
---

# ## OAG Batch Indexing: Pipeline Reliability Lessons

## OAG Batch Indexing: Pipeline Reliability Lessons

### Context
Ingesting 545 คำวินิจฉัยอัยการสูงสุด into Thai Legal RAG — added topic filtering, fixed Gemini stream hang.

### Pattern: Gemini Stream Can Hang Indefinitely
`generate_content_stream` has no default timeout. On certain PDFs, the SSE connection stays open but no data returns. Always set `http_options.timeout: 120` for any streaming Gemini call.

### Pattern: Topic Filter at Index Time, Not Query Time
Filter irrelevant documents at ingestion — keyword match on document text before OCR. Only 57% of OAG documents were procurement-related; without filtering, 5,000+ irrelevant chunks would degrade all queries.

### Pattern: Backup Before Delete (Atomic Swap)
Before deleting index files for rebuild:
1. Rename to `.bak` instead of `rm` (rename to backup)
2. OR build into new directory and swap atomically

Deleting and then failing the rebuild leaves system non-functional for hours. Rate limit failures on single API key + 500+ embedding calls are predictable — flag this risk before starting.

### Pattern: Periodic Checkpoint in Batch Pipelines
Large batch pipelines (1000+ files) should save index state every N files. If pipeline hangs/fails midway, all progress since last save is lost. FAISS index save happens only at the end by default.

### Pattern: Authority Hierarchy Requires Structure
When indexing documents from multiple authority levels (อัยการ > กวจ), you need metadata to know which source trumps which. Document type and issuing authority must be stored in payload for future filtering.

---
*Added via Oracle Learn*
