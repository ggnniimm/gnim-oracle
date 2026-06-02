# Prod BM25 corruption + ID-query is a rerank problem (not pool injection)

**Date**: 2026-06-02
**Context**: Resuming the 2026-05-28 ID-query bug (ว397 "not found"). Before building
the handoff's "Option 4" (filename injection), re-synced local to prod and
re-measured on a clean index. Two big findings flipped the plan.

## Finding 1 — prod BM25 was badly corrupted (live prod bug)

Pulled prod `bm25.pkl` (151M, dated 2026-05-29 04:32) and loaded it:
- **68,359 entries** vs Qdrant exact **34,212** (≈2×)
- 27,572 (file_id, chunk_index) signatures appeared 2–9× (duplicates)
- unique signatures 38,504 > Qdrant 34,212 → **4,292 stale chunks** in BM25 not in Qdrant
  (left behind when inactive-cleanup deleted them from Qdrant but not BM25)

**Root cause**: force-reindex **appends** to BM25 without dedup. Timeline proves it:
handoff rebuilt BM25 to 34,124 on 05-28 morning; by 05-29 it was 68,359 — the
evening 17-file force-reindex batch re-doubled it. This is issue #42.

**Rule**: the deploy/reindex step must **REBUILD** BM25 from Qdrant, never append.
New tool: `pipeline/rebuild_bm25_from_qdrant.py` (scrolls Qdrant → wipes → rebuilds →
verifies count match + zero dup signatures). Source = **Qdrant**, never md_backup
(md_backup has 1,401+ files incl. orphans not in Qdrant). Decision (Ming, 06-02):
fix prod BM25 at Option 4 deploy time, not a separate hotfix.

## Finding 2 — clean BM25 alone fixed 2 of 3 "misses"; ว397 is a RERANK problem

Re-ran the handoff's 8-doc ID-query test (`pipeline/measure_id_query_rank.py`) on the
clean-BM25 local (code == prod HEAD, uncommitted refinement stashed):

| Doc | Handoff (corrupt BM25) | Clean BM25 | Note |
|---|---|---|---|
| ว298/299/651/189 | 1 | 1 | fine |
| ว214 | MISS | **3** | fixed by clean BM25 |
| ว181 | MISS | **8** | fixed by clean BM25 |
| ว110 | MISS | MISS | **not in corpus** — no "ว ๑๑๐" ref, no ว_110 doc; not a bug |
| ว397 | 10 | 10 | still low |

ว397 deep-check: BM25 ranks it **#1**, vector pool #10, but after fusion with 422
vector results rerank dilutes it to **rank 10/40**. The chunk is ALREADY in the pool
→ "Option 4" (filename injection into pool) would NOT help.

`is_specific_query("ว 397")` = **False**. `_SPECIFIC_PATTERNS` catches bare 4+ digit
doc IDs (`\b\d{4,}\b`) and มาตรา/ข้อ/หมวด/วรรค, but **not "ว NNN"** (3 digits + ว prefix).
The retriever already has a "specific query → BM25-authoritative" path; the fix is to
make `is_specific_query` recognize `ว\s*[\d๐-๙]{1,4}` so ID queries route there → ว397
goes to rank 1. **Option 4 redesign: extend is_specific_query, not pool injection.**
Caveat: only fixes ID-style queries ("ว 397"); content queries about ว397 rely on the
already-deployed Phase 1.1 glossary + the stashed vocab_expand refinement.

## Method note
- Made local a faithful mirror of prod via Qdrant snapshot restore (same v1.17.1 commit),
  NOT re-index — guarantees byte-equal vectors. Then rebuilt BM25 from that Qdrant.
- Qdrant ITSELF has ~1,849 true-dup chunks + 755 stale-collision (re-OCR without delete)
  — pre-existing on prod, separate cleanup task, not chased here.

## Finding 3 — A vs B both fix the rank; choice is design, not eval (0 blast radius)

Implemented both fixes and measured ว-NNN ranks on clean-BM25 local:

| Doc | B0 (clean, no fix) | A (is_specific_query) | B (reranker boost) |
|---|---|---|---|
| ว397 | 10 | **1** | **1** |
| ว214 | 3 | 1 | 1 |
| ว181 | 8–9 | 1 | 1 |
| ว298/299/651/189 | 1 | 1 | 1 |
| ว110 | MISS | MISS | MISS (not in corpus) |

- **A** = add `r"(?:^|\s)ว\s*[\d๐-๙]{1,4}\b"` to `_SPECIFIC_PATTERNS` (query_expand.py, 4 lines).
  ID queries route to the existing "specific → BM25-authoritative" path (no vector, no
  Gemini expand). Patch: `option4_patches/approach_A_is_specific_query.patch`.
- **B** = dynamic ID-match boost in reranker.py (~30 lines, `ID_MATCH_BOOST=5.0`): keeps full
  hybrid pool + Gemini expansion, ×5 boosts chunks of the named circular.
  Patch: `option4_patches/approach_B_reranker_id_boost.patch`.

**Key result: 0 of 84 golden TCs match the `ว NNN` pattern** → neither A nor B changes ANY
existing TC's behavior → both are **provably regression-free on the eval set** without running
the 84-TC eval. The full eval is still wanted once (network permitting) to validate the
clean-BM25 change for non-ID queries, but it does NOT gate the A-vs-B choice.

**Discriminator (advisor's catch — the golden set has 0 ID queries so it can't compare A/B).**
Ran ID+content queries through both (`pipeline/inspect_topk.py`):
- "ว 397 ผ่อนผันเรื่องอะไร": **A** → ว397 dominates (ranks 1,3,6,8,9) MIXED with related ผ่อนผัน
  circulars (ว1203, ว1225) — healthy. **B (×5)** → top-10 are ALL ว397 chunks, context destroyed.
- "ว 214 กำหนดกรอบระยะเวลา": **A** → ว214 at rank 7 + content-relevant docs. **B (×5)** → top-10
  ALL ว214.
- Baseline B0: target buried out of top-10 in both (the actual bug for content+ID queries).

Conclusion: A's BM25-only does NOT starve context — content words still match neighbours
lexically. B's ×5 boost is **overtuned**: it beats MMR diversity and floods top-K with one doc.

**Recommendation: A** — 4 lines, extends the existing documented architecture ("doc-ID lookup →
BM25 authoritative; vector embeddings of bare numbers are noise"), gives target-prominent +
context, avoids Gemini cost for ID lookups. B would need its boost tuned down (×1.5?) just to
match what A does for free. B's theoretical edge (semantic context) didn't materialise — A keeps
context, B loses it.

**Eval env note (2026-06-02)**: local eval blocked intermittently — Vertex `generateContent`
"Connection reset by peer" (Errno 54) even on hotspot, AND embed 429 RESOURCE_EXHAUSTED at
workers=4 (use workers=1). Retrieval-only measurement works through the flakiness; full
generate-eval does not reliably. Deferred the 84-TC baseline to when Vertex is stable.

## Deploy bundle (when ready, per Ming)
clean-BM25 rebuild on prod (NOT append — fixes Finding 1) + Approach A (or B) + the stashed
vocab refinement, all together; then re-run 84-TC eval and prod smoke "ว 397" → rank 1.

See also: [[2026-05-28_destructive-defaults-are-tech-debt]], handoff
`2026-05-28_21-50_corpus-cleanup-orphan-discovery-and-id-query-bug.md`.
