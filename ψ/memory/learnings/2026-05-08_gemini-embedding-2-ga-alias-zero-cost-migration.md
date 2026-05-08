# gemini-embedding-2 GA = preview alias on `global` endpoint — zero-cost migration

**Date**: 2026-05-08
**Context**: thai-legal-rag — quota wall on `gemini-embedding-2-preview` (us-central1, ~7-10 calls/min)

## Discovery

Yesterday (2026-05-07) we built multi-pool round-robin infra to bypass per-region quota for `gemini-embedding-001`. Today probed `gemini-embedding-2` GA again — turned out it shipped on Vertex via a **new endpoint pattern**: `location='global'`, not regional.

## Key facts (probed and verified 2026-05-08)

1. **`gemini-embedding-2-preview` ≡ `gemini-embedding-2` GA** — they are the **same model under different aliases**. Cross-cosine = **1.000000** across all task_types (RETRIEVAL_DOCUMENT, RETRIEVAL_QUERY, SEMANTIC_SIMILARITY) and all texts (Thai legal + English). Vectors are byte-identical.
2. **v2 GA available only on `location='global'`** — all regional endpoints (us-central1, us-east1, ..., asia-northeast1) return 404 NOT_FOUND. Both `gen-lang-client-0136329629` and `ambient-odyssey-494206-p5` projects work on global.
3. **Global endpoint quota = ~40-60× regional** — burst test 30 parallel calls in 4.1s = **435 calls/min** with **zero 429s**, vs regional preview's ~7-10 calls/min ceiling.
4. **`gemini-embedding-2-preview` itself only exists in us-central1** — confirmed 404 in us-east1, us-west1, europe-west1, asia-southeast1, etc. (Yesterday's multi-region test was for `gemini-embedding-001`, not preview.)

## Migration recipe (zero re-index, zero re-validation)

Because vectors are identical, **no re-index needed** for the existing 28K-chunk corpus. Just flip 2 env vars + the model name:

```diff
# .env
-GOOGLE_CLOUD_LOCATION=us-central1
+GOOGLE_CLOUD_LOCATION=global
+EMBEDDING_MODEL=gemini-embedding-2

# src/config.py (if hardcoded, not env-readable)
-GEMINI_EMBEDDING_MODEL = "gemini-embedding-2-preview"
+GEMINI_EMBEDDING_MODEL = "gemini-embedding-2"
```

Verified prod: TC-014 40.4s with no retries (vs 111s with 429 retry before migration). TC-035 PASS.

## Gotchas hit

- **`docker compose restart` does NOT reload `.env`** — only `docker compose up -d` recreates the container with new env vars. Verified: after `restart`, container env still showed old values; after `up -d`, new values loaded.
- **Image was built with hardcoded `gemini-embedding-2-preview`** — even after .env loaded `EMBEDDING_MODEL=gemini-embedding-2`, the constant stayed at preview because src/config.py was the older non-env-reading version. Fix: sed-edit prod source + `docker compose build app`.
- **Multi-pool infra (yesterday's work) not needed** for this migration — global quota is plenty for 28K-chunk re-index even if we ever wanted one. Multi-pool code stays uncommitted as future option.

## Why it matters

- **Future-proof**: preview models get deprecated post-GA. Migrating now avoids forced migration later.
- **Quota wall gone**: prod was hitting 429s during normal user traffic on preview. Global resolves this.
- **Spec headroom**: v2 spec includes 8K tokens, MRL truncation, OCR, multimodal — all available now without further migration.

## Related

- 2026-05-07 handoff: `vertex-multi-pool-quota-bypass.md` (multi-pool round-robin — superseded by this finding)
- 2026-05-04 learning: `vertex-multi-pool-per-region-quota.md` (per-region quota — still true, but irrelevant for v2 GA on global)
