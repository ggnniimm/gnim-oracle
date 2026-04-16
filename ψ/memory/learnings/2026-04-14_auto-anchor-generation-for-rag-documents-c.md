---
title: ## Auto-Anchor Generation for RAG Documents
tags: [rag, retrieval, anchors, gemini, batch-processing, thai-legal-rag]
created: 2026-04-14
source: Oracle Learn
---

# ## Auto-Anchor Generation for RAG Documents

## Auto-Anchor Generation for RAG Documents

### Context
Thai Legal RAG project with 970 MD files, initially only 9 had manual `## บทสรุปสำหรับสืบค้น` retrieval anchors.

### Pattern: Simple Prompts Produce Good Retrieval Anchors
`"15-20 keywords + 2-3 sentences, plain text"` → Gemini consistently generated high-quality retrieval anchors across 970 diverse legal documents (99.8% success rate).

### Pattern: Idempotency via has_anchor() Check
Batch generation script must check `has_anchor()` before processing each file — skips already-processed files. Makes the script safe to re-run after failures without double-appending.

### Pattern: sys.path.insert in All Pipeline Scripts
All pipeline scripts in this project use:
```python
sys.path.insert(0, str(Path(__file__).parent.parent))
```
to import from `src/`. Must include this for any new pipeline script.

### Pattern: Build Retry Logic into Batch Scripts
A simple `for attempt in range(3)` wrapper with exponential backoff around Gemini calls makes batch scripts truly fire-and-forget. Without it, transient 429 failures require manual `--file` retries.

### Result
Added 2,163 new anchor chunks to 970 files. Eval stable at 8/8 PASS with no regressions.

---
*Added via Oracle Learn*
