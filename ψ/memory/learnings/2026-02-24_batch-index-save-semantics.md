# Lesson: Batch Indexing Save Semantics & Progress Monitoring

**Date**: 2026-02-24
**Source**: thai-legal-rag re-index session (CGD1+2+3)

## Core Lesson

In `batch_index.py`, different storage layers have different save timing:

| Storage | Save timing | Interruptible? |
|---------|-------------|----------------|
| `dedup.db` | Per-chunk (real-time) | Yes — survives kill |
| `ocr_cache/` | Per-file (real-time) | Yes — survives kill |
| `faiss_index/` | End of process only | No — lost if killed |
| `bm25_index/` | End of process only | No — lost if killed |

**Consequence**: Killing a batch mid-run leaves dedup.db with hashes for files that aren't in FAISS. Next run will skip those files (dedup says indexed) but FAISS won't have them. Result: permanently missing vectors.

**Recovery if killed mid-run**: Wipe dedup.db + FAISS + BM25, re-run from scratch. OCR cache survives so re-OCR is fast.

## Progress Monitoring Pattern

When TaskOutput buffer is capped and FAISS is unreadable mid-run, use dedup.db as real-time proxy:

```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('data/dedup.db')
total = conn.execute('SELECT COUNT(*) FROM indexed_chunks').fetchone()[0]
baseline = 13836  # count before this run
new_chunks = total - baseline
avg_per_file = 13  # estimate from first N files
print(f'Estimated files done: {new_chunks // avg_per_file}')
conn.close()
"
```

## Failed Log Improvement (Pending)

Current: `failed.append(file_id)` — only ID, no filename
Better: `failed.append(f"{file_id}  # {file_name}")` — human-readable

## Tags

batch-indexing, faiss, dedup, progress-monitoring, save-semantics, thai-legal-rag
