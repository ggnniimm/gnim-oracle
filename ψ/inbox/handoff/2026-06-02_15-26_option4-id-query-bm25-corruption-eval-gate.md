# Handoff: Option 4 (ID-query fix) + BM25 corruption + eval gate

📡 Session: d7cc9648 | gnim-oracle/thai-legal-rag | ~8h
**Date**: 2026-06-02 15:26 +07
**Context**: Started as "what does Option 4 do?" → became a full diagnose+fix+eval arc

## What We Did

### Data re-sync (local → faithful mirror of prod)
- Restored local Qdrant from prod snapshot (same v1.17.1) → **local == prod 34,212 exact**
- Backups durable: `data/qdrant_snapshots_backup/`, `bm25.pkl.bak.pre-resync-2026-06-02`

### Found + fixed (locally) prod BM25 corruption
- Prod `bm25.pkl` = **68,359** vs Qdrant 34,212 — duplicates (27,572 sigs ×2-9) + 4,292 stale
- Root cause: force-reindex APPENDS to BM25 without dedup (issue #42)
- New tool `pipeline/rebuild_bm25_from_qdrant.py` → local BM25 clean (34,212, REBUILD not append)
- Also found Qdrant itself has ~1,849 true-dup + 755 stale-collision chunks (separate cleanup)

### Option 4 redesigned + chosen (Approach A) — committed `08012a0`
- Original "filename injection" was wrong: ว397 is in pool (BM25 #1) but rerank dilutes to ~10
  → it's a RERANK/routing issue, not a pool issue
- clean BM25 alone fixed ว214/ว181; ว110 not in corpus (not a bug)
- **A** = add `ว NNN` to `_SPECIFIC_PATTERNS` (query_expand.py) → ID queries → existing
  BM25-authoritative path → all in-corpus ว-docs rank 1
- **B** (reranker ×5 boost, `option4_patches/`) rejected: floods top-K, destroys context
- Discriminator (`inspect_topk.py`): A keeps context, B floods. 0/84 TCs match ว-NNN → bundle
  is regression-free on eval set
- Also committed the **vocab_expand refinement** (content-query path; users query both ways)

### Clean-BM25 baseline eval = 71/75 (9 SKIP) — gate found 1 real regression
- Run unbuffered (`python3 -u` — block-buffering hid all progress, killed several working runs)
- 4 FAIL: TC-067/TC-074 = known intermittents; **TC-044, TC-077 = consistent**
- Prod comparison (SSH on home network): **TC-044 FAIL on prod too = pre-existing** (deploy-safe);
  **TC-077 PASS×3 on prod but FAIL on clean local = regression** — prod PASS was an ARTIFACT of
  BM25 duplicates boosting ว122. Content (ว122, มาตรา102+อุทกภัย) EXISTS in Qdrant → fix with a
  legitimate ranking boost/cross-ref.

## Pending
- [ ] Fix TC-077 ranking — boost/cross-ref ว122 (มาตรา102 + เหตุสุดวิสัย อุทกภัย/น้ำท่วม)
- [ ] Optional: fix TC-044 (pre-existing — 52101 not ranked into top-27; cross-ref injection)
- [ ] Re-run 9 API-SKIP TCs (TC-001/003/006/007/011/013/014/027/079) for full baseline
- [ ] Deploy bundle: prod BM25 rebuild-from-Qdrant + push `08012a0` + image, then smoke "ว 397"→rank 1

## Next Session
- [ ] `/recap` to reload
- [ ] On hotspot (Vertex works): iterate TC-077 ranking fix + local eval to confirm
- [ ] On home (SSH works): prod re-checks + deploy
- [ ] Run full 84-TC eval once more clean → confirm 82+/84 before deploy

## Key Files
- `src/retrieval/query_expand.py` — Approach A (committed)
- `src/retrieval/glossary.py`, `retriever.py` — vocab refinement (committed)
- `src/retrieval/reranker.py` — where TC-044/077 ranking fix goes (cross-ref/boost)
- `pipeline/rebuild_bm25_from_qdrant.py` — deploy MUST rebuild BM25 (never append)
- `pipeline/measure_id_query_rank.py`, `inspect_topk.py` — measurement tools
- `option4_patches/` — A & B patches (B kept for reference)
- `ψ/memory/learnings/2026-06-02_bm25-corruption-and-id-query-rerank.md` — full findings

## Gotchas (this session)
- **Network is either/or**: hotspot = Vertex generate works but SSH port 22 to prod blocked (ISP);
  home = SSH works but Vertex generate resets. Pick per task.
- **Eval output buffers** — always `python3 -u` / PYTHONUNBUFFERED=1, redirect to file (never tail).
- **Embed 429** at workers=4 → use **workers=1** for local eval.
- Vertex generate intermittently 429/resets → some TCs SKIP (per-TC 120s timeout); re-run with --id.

## Production State
- Server 31.97.188.155 (root@) — SSH only on home network
- Qdrant exact: **34,212** | prod BM25 CORRUPTED at 68,359 (fix at deploy via rebuild)
- Prod code == local HEAD (before `08012a0`); bundle NOT yet deployed
- eval runner on prod: `/app/pipeline/run_eval.py` (local is `eval/run_eval.py`)
