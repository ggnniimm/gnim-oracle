# Handoff: Vertex AI multi-pool quota bypass + gemini-embedding-001 evaluation

📡 Session: 335e39e4 | gnim-oracle | ~3h
**Date**: 2026-05-07 17:00
**Context**: thai-legal-rag — explored migrating from `gemini-embedding-2-preview` to GA models, hit quota wall, discovered multi-region/multi-project bypass

## What We Did

### Studied Vertex embedding docs
- Confirmed **`gemini-embedding-2`** GA exists (released 2026-04-22) — 8K tokens, MRL, OCR, multimodal — but **404 NOT_FOUND on this project** (us-central1). Not yet rolled out / needs allowlist.
- Available on this project: `gemini-embedding-2-preview` (current), `gemini-embedding-001` (GA), `text-multilingual-embedding-002`, `text-embedding-005`
- task_type values, dim/token limits documented

### Stage 0: Cross-model sanity check
- preview vs 001 cross-cosine = **0.02** (vector spaces totally different — must re-index if migrating)
- Within-model: preview unrelated 0.41–0.54 mean / related 0.68–0.89; 001 unrelated 0.47–0.59 / related 0.80–0.86
- Both models normalize correctly (L2=1.0). Verified the 0.02 cross-cosine is real, not a test bug.

### Stage 1: Shadow eval (5 TCs, no writes)
- TC-014, TC-035, TC-049, TC-063 (corpus-gap), TC-077 — all answer-bearing chunks rank 1 under both preview and 001
- **No signal that 001 retrieval quality is worse than preview** within preview's top-25 candidates

### Stage 2: Mini parallel index (10 docs under 001)
- **First attempt — single client**: 0/10 docs in 4 min (constant 429 RESOURCE_EXHAUSTED)
- **Discovery**: Vertex AI quota is **per-(project, region, model) per-minute**. Verified vectors are identical across regions/projects (cosine=1.000000).
- Built **multi-pool round-robin** client (5 regions × gen-lang + 2 × ambient-odyssey = 7 pools)
- **Second attempt — multi-pool**: 10/10 docs (250 chunks) in 9 min, **0 retries**, ~28 chunks/min effective throughput
- Smoke retrieval test on 250-chunk corpus: 4/5 TCs answer-bearing chunk in top-5 (TC-077 fails because law file not in subset)

## Code Changes (uncommitted, all backwards-compatible)

- `src/config.py` — `DEDUP_DB`, `BM25_DIR` env-overridable (default unchanged)
- `src/gemini_client.py` — added `get_pool_client()` reading `VERTEX_POOLS` env (JSON list of `{project, location, sa_path?}`)
- `src/indexing/qdrant_store.py` — `_embed_one()` now uses `get_pool_client()` (was `get_client()`)
- `scripts/compare_embed_models.py` — embedding model comparison helper (kept)

**Default behavior unchanged when `VERTEX_POOLS` is unset.** Prod rebuild = no-op unless env set.

## Pending

- [ ] Decide whether to deploy `VERTEX_POOLS` to prod `.env` (5x throughput, no migration needed)
- [ ] Decide whether to migrate to `gemini-embedding-001` GA (requires re-index 28K chunks + re-validate baseline 84/84)
- [ ] Wait for `gemini-embedding-2` GA to roll out to project (or request allowlist)
- [ ] Save findings to memory: multi-pool throughput recipe, vector identity across regions, quota is per-pool not platform-wide
- [ ] Decide cleanup: drop `thai_legal_rag_001_test` collection in local Qdrant (250 points, harmless) or keep for future

## Next Session

- [ ] Save 3 learnings to memory (multi-pool, vector-identity, 001-as-fallback)
- [ ] If continuing migration thesis: index full corpus under 001 in local thai_legal_rag_001 with multi-pool — ETA ~50 min for 28K chunks at 28 chunks/min × 7 pools (parallelized) — then run full eval subset
- [ ] If pausing migration thesis: revert/keep code patches, document quota-bypass for future reference, ship `VERTEX_POOLS` to prod `.env` for current preview model speedup

## Key Files

- `ψ/lab/thai-legal-rag/src/gemini_client.py` — `get_pool_client()` is the new infra
- `ψ/lab/thai-legal-rag/src/indexing/qdrant_store.py` — `_embed_one()` now uses pool
- `ψ/lab/thai-legal-rag/src/config.py` — DEDUP_DB/BM25_DIR env support
- `ψ/lab/thai-legal-rag/scripts/compare_embed_models.py` — model A/B compare util
- `/tmp/embed-compare-venv/` — isolated test venv (not committed)
- `/tmp/stage1_shadow_eval.py`, `/tmp/stage2_smoke.py` — experiment scripts

## VERTEX_POOLS recipe (for prod or future use)

```bash
VERTEX_POOLS='[
  {"project":"gen-lang-client-0136329629","location":"us-central1"},
  {"project":"gen-lang-client-0136329629","location":"us-east1"},
  {"project":"gen-lang-client-0136329629","location":"us-west1"},
  {"project":"gen-lang-client-0136329629","location":"europe-west1"},
  {"project":"gen-lang-client-0136329629","location":"asia-southeast1"}
]'
```

(Optional: add `{"project":"ambient-odyssey-494206-p5",...,"sa_path":"..."}` for 2x more pools, but SA key would need to be mounted on prod.)
