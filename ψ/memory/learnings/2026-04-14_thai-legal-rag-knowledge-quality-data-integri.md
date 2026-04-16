---
title: ## Thai Legal RAG Knowledge Quality + Data Integrity Patterns (2026-02-23 to 202
tags: [faiss, data-integrity, index-rebuild, metadata-prefix, dedup, thai-legal-rag, knowledge-quality, document-superseded]
created: 2026-04-14
source: retro: 2026-02-23 to 2026-02-24 knowledge quality + faiss misalignment
---

# ## Thai Legal RAG Knowledge Quality + Data Integrity Patterns (2026-02-23 to 202

## Thai Legal RAG Knowledge Quality + Data Integrity Patterns (2026-02-23 to 2026-02-24)

**Superseded notes in MD > silent deletion**: When a document is superseded (e.g., กวจ ๐๕๒๓ superseded by ว 476), add explicit "Superseded" note to the MD file and re-embed. LLM sees the note and knows to discard. Honest about history without hiding it.

**ว ซ้อมความเข้าใจ is authoritative re-statement, not commentary**: A หนังสือเวียน ซ้อมความเข้าใจ corrects wrong interpretations — it supersedes, not merely clarifies. Important for legal document categorization.

**FAISS has no delete API — metadata-only cleanup causes misalignment**: Removing entries from metadata.pkl without rebuilding FAISS leaves orphan vectors at wrong positions. Any chunks indexed after the cleanup are at wrong positions in FAISS — they become "invisible" despite existing in metadata. Fix: add `if idx >= len(metadata): continue` guard, then rebuild the full index with `rebuild_faiss_index.py`.

**dedup.db as progress proxy for long-running background index**: When FAISS saves only at end and TaskOutput buffer caps, read dedup.db real-time: `new_chunks / avg_chunks_per_file ≈ files_indexed`. Useful pattern: when you can't read the destination, read the real-time side channel.

**Drive shared folder access**: `list_files()` needs `supportsAllDrives=True` + `includeItemsFromAllDrives=True` for files in shared drives. Missing these flags returns 0 results silently.

**Wrong legal answers without source documents**: When LLM hedges and retrieved chunks don't definitively answer, don't substitute own reasoning. Say "the retrieved chunks don't cover this definitively" — never fill gap with legal interpretation. Always read actual document chunks before reporting an answer.

**Doc numbers not searchable without metadata prefix**: Query by document number ("มีหนังสือเลข 5529") fails because BM25/FAISS search content, not metadata. Fix: prepend `_metadata_prefix()` (doc_number, date, issuer) to chunk text at indexing time.

**Knowing save semantics of each storage layer**: dedup.db = real-time updates. FAISS/BM25 = save at end of batch. Never stop mid-process when dedup.db and FAISS would become out of sync. Explain this clearly before any long-running re-index.

---
*Added via Oracle Learn*
