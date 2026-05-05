# Embedding model is NOT a pluggable component in a tuned RAG

**Date**: 2026-05-04
**Source**: OpenAI text-embedding-3-large experiment — thai-legal-rag

## The Lesson

In a RAG system that has been tuned via cross-reference injection, chunk promotion, guide document content, and anchor generation, the **embedding model is the lens through which all that tuning was done**. Swapping the embedding model to a different provider (even same dimensionality, same quality) invalidates all retrieval tuning.

**Evidence**: Switched from `gemini-embedding-2-preview` (Vertex AI) to `text-embedding-3-large` (OpenAI), both dim=3072, same corpus. Result: 70/81 PASS vs prod 84/84. TC-063 retrieval trace showed OpenAI ranking completely different documents — not because the info isn't there, but because geometric distances are different in OpenAI's embedding space.

## Why This Matters

All the following RAG improvements are embedding-space-specific:
- Cross-reference injection (inject content into top-retrieved doc for a specific query)
- Chunk promotion (move key phrases to early positions because retrieval is score-ranked)
- Guide document tuning (add explicit criteria language to help the model surface the right chunk)
- Rescue phrases (trigger on specific query patterns that reliably retrieve a target doc)

If you change the embedding model, the "top-retrieved doc" for each query changes → cross-refs no longer help → all tuning is lost.

## What This Means for Migration

Switching embedding models is a **full migration**, not a configuration change:
1. Re-embed entire corpus with new model
2. Re-run full eval to get new baseline
3. Re-diagnose all failures (different docs retrieved → different failure modes)
4. Re-apply cross-refs, chunk promotions, guide docs for new retrieval pattern
5. Re-run eval until target score

Budget: weeks of work, not hours.

## Alternative: Vertex AI Quota Increase

For the thai-legal-rag project, the right path is:
- Request `aiplatform.googleapis.com/online_prediction` quota increase on `gen-lang-client-0136329629`
- URL: https://console.cloud.google.com/iam-admin/quotas?project=gen-lang-client-0136329629
- Filter: "online_prediction" → request 600/min (from ~3 RPM current)
- This preserves all tuning, same embedding space, just faster

## OpenAI Code Is Useful Anyway

If intentional migration ever happens (with proper re-tuning budget), the OpenAI batch API code is ready:
- 100 texts per API call (vs Gemini's forced 1-at-a-time due to Vertex batch bug)
- ~2 hours to index 28K chunks vs 6+ hours with Vertex at ~3 RPM
- Isolated via `QDRANT_URL + QDRANT_COLLECTION + EMBEDDING_MODEL` env vars

## Vertex AI Quota Is PROJECT-LEVEL

Separate but related lesson from same session: Vertex AI quota for `online_prediction` is shared across ALL models on the project. Switching from `gemini-embedding-2-preview` to `text-multilingual-embedding-002` to `text-embedding-005` all hit the same 429. Model switching cannot bypass project-level quota limits.
