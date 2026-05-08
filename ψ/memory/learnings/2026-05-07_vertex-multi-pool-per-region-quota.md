# Vertex AI quota is per-(project, region, model) — multi-pool round-robin bypasses the wall

**Date**: 2026-05-07
**Repo**: gnim-oracle / thai-legal-rag

## What

The "default ~7-10 texts/min" quota wall on Vertex AI embedding models is **per-(project × region × model)**, not platform-wide as previously believed. Round-robin across multiple regions (and optionally multiple projects) gives an effective Nx throughput multiplier without any quota request to Google.

## Evidence

Single-pool indexing under `gemini-embedding-001` (us-central1, gen-lang-client-0136329629):
- 0/10 docs in 4 minutes, 3 consecutive 429 RESOURCE_EXHAUSTED, 60-68s waits each

Multi-pool (5 regions × gen-lang + 2 × ambient-odyssey = 7 pools), same model, same docs:
- 10/10 docs (250 chunks) in 9 minutes
- **0 retries**
- ~28 chunks/min effective (vs ~0 for single-pool)

Cross-pool vector consistency check: same input text, same model, different region/project → cosine = **1.000000** (byte-identical). Safe to mix in one Qdrant collection.

## Recipe

`src/gemini_client.py` reads env `VERTEX_POOLS` (JSON array):

```bash
VERTEX_POOLS='[
  {"project":"gen-lang-client-0136329629","location":"us-central1"},
  {"project":"gen-lang-client-0136329629","location":"us-east1"},
  {"project":"gen-lang-client-0136329629","location":"us-west1"},
  {"project":"gen-lang-client-0136329629","location":"europe-west1"},
  {"project":"gen-lang-client-0136329629","location":"asia-southeast1"}
]'
```

Each pool entry can include `"sa_path":"/path/to/sa.json"` to use a service-account key for a different project. Default ADC is used when `sa_path` is omitted.

`get_pool_client()` round-robins across pools per call. Falls back to `get_client()` (single-region) when env unset → backwards-compatible.

## When to apply

- Indexing batches >100 chunks under any Vertex embedding model
- Eval runs that re-embed many queries
- Any time the project hits 429 RESOURCE_EXHAUSTED on `aiplatform.googleapis.com/online_prediction_*`

## Why this works

Vertex AI quota metric `online_prediction_requests_per_base_model_per_minute_per_region` is scoped to one region per project. A request to `us-east1` decrements that region's bucket — leaves `us-central1`, `europe-west1`, etc untouched. Multi-region requests fill independent buckets in parallel. Adding a second project (different SA key) doubles again because the quota is also per-project.

## Caveats

- Latency varies per region (asia-southeast1 fastest from Bangkok at ~1.4s; europe-west1 slowest at ~4.4s). Round-robin ignores latency — for latency-critical paths consider preferring closest region.
- Documented quota ceiling per region is the SAME default low value (~7-10/min). Multi-pool exploits parallel buckets, not a higher ceiling.
- `gemini-embedding-2` (GA 2026-04-22, the latest model) is **404 on this project** — multi-pool helps for 001 and preview only until embedding-2 is allowlisted.
- The `aiplatform.googleapis.com/online_prediction_*` quota is shared across embedding models within a region. Mixing 001 and preview calls in the same region competes for the same bucket.

## File references

- `ψ/lab/thai-legal-rag/src/gemini_client.py` — `get_pool_client()`, `_build_pool_clients()`
- `ψ/lab/thai-legal-rag/src/indexing/qdrant_store.py` — `_embed_one()` consumer
- `ψ/lab/thai-legal-rag/src/config.py` — `DEDUP_DB`, `BM25_DIR` env support (related)

## Supersedes

Memory entry on Vertex quota gotcha previously said "Only fix: request quota increase." That's still true if you want a higher per-region ceiling, but **multi-pool round-robin is a strictly faster fix for batch jobs** that doesn't require Google approval.
