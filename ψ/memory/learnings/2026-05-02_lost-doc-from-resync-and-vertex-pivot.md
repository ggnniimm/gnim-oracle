# Lost-doc-from-resync + AI Studio → Vertex AI pivot

**Date**: 2026-05-02
**Triggers**:
1. Path A surgery on doc 51349 didn't fix TC-082 (mode-1 retrieval/quoting)
2. Local TC-082 3/3 PASS but prod 0/3 FAIL — content drift, not double-indexing
3. AI Studio prepayment credits depleted mid-session, blocking eval

## Three lessons from one session

### 1. Local Qdrant content drift, not just chunk-count drift

The "local has double-indexed chunks, don't trust local eval" warning in MEMORY was correct but incomplete. Local Qdrant *also* has docs that prod doesn't — specifically a synthetic calculation guide (`แนวทาง_การคำนวณค่าปรับ_บริหารสัญญา.md`) that was indexed locally and survived the 04-30 corpus resync because local Qdrant wasn't fully wiped.

When TC-082 PASSed locally and FAILed on prod, the natural assumption was "double-indexing screwed up rerank ordering." The actual cause was much simpler: **local cited a doc prod didn't have**. The fix was diff'ing the retrieved sources between local and prod runs — within seconds the difference was obvious.

**Saved as**: `feedback_local_eval_content_drift.md`. Rule: when local PASSes and prod FAILs, diff `Sources :` lines first; content drift is faster to spot than rerank variance.

### 2. Corpus resync casualty audit must be routine

The 04-30 resync rebuilt `gnim-oracle/.../md_backup/` from sibling `gnim-oracle-qdrant`. Sibling didn't have the synthetic guide doc (created 2026-04-24 from a YouTube tutorial, only added to gnim-oracle directly). When sibling content overwrote gnim-oracle's md_backup, the guide vanished. Prod corpus rebuilt from the now-gutted gnim-oracle directory inherited the loss.

The casualty was invisible until TC-082 went 0/3 again. There was no error, no missing-file warning, no diff in chunk counts — just a doc that was there yesterday and gone today.

**Recovery enabled by**: `/tmp/prod_md_backup_2026-04-29/` — a snapshot taken before the resync. Without that snapshot the doc would be effectively lost (the YouTube source URL is in frontmatter but re-deriving the doc would mean re-watching the tutorial).

**Rule going forward**: after any corpus resync, run
```bash
diff <(ls /tmp/prod_md_backup_<DATE>/ | sort) <(ls <canonical>/md_backup/ | sort)
```
to enumerate casualties. A fresh snapshot before each resync is the rollback floor.

### 3. AI Studio → Vertex AI pivot under quota pressure

Mid-session, AI Studio key returned `Your prepayment credits are depleted` on both `gemini-2.5-flash` and `gemini-embedding-2-preview`. Two new keys Ming generated had the same depletion (same project's billing). The fix was switching auth backend, not key.

GCP $300 free credit (claimed 2026-04-XX, 90-day window) covers Vertex AI. Pivot took ~30 min:
- gcloud auth login + ADC + enable aiplatform.googleapis.com
- Create service account with `Vertex AI User` role, download JSON key
- Add `USE_VERTEX_AI` toggle in src/config.py via `GOOGLE_CLOUD_PROJECT` env
- get_client() routes to vertexai mode when project is set
- scp SA key to prod, mount as `/app/credentials/sa.json`, update prod docker-compose + .env

**Vector compatibility verified**: cosine 1.0 between Vertex-generated embedding and prod Qdrant stored vector for the same input. Same model (`gemini-embedding-2-preview`), just different endpoint. No re-index needed.

**Three SDK gotchas that ate ~45 min**:

1. `google-genai==1.63.0` returns `400 FAILED_PRECONDITION` for `gemini-embedding-2-preview` on Vertex. 1.74.0 fixes it. Local had 1.66.0 (worked); prod had 1.63.0 (didn't). Pinned `>=1.74.0`. Same model, same SA, same project — only difference was SDK version.

2. Vertex 404s on `models/X` model names; AI Studio is forgiving and accepts both. Stripped `models/` prefix from `GEMINI_EMBEDDING_MODEL`. AI Studio mode still works — the bare name is accepted by both.

3. `gemini-2.0-flash` (used in `eval/run_eval.py:63` for semantic_check) is not in `us-central1` on Vertex (but is on AI Studio everywhere). Swapped to `gemini-2.5-flash`. Region availability differs between AI Studio (global) and Vertex AI (per-region).

### Quota gotcha: preview models start at ~3 RPM on new GCP projects

Default quota for `aiplatform.googleapis.com/online_prediction_requests_per_base_model` with `base_model:gemini-embedding-2` is **~3 RPM** on a fresh GCP project. Burst test confirmed: 3 calls succeed, 4th 429s. Eval that needs ~5-6 embeds per TC × 84 TCs = 500 embeds, 167 minutes at 3 RPM. Acceptable but slow.

Workaround: aggressive backoff in `_embed` — 60s+30s/attempt + jitter, 8 retries total. TC works after waiting ~70s for window reset. For full eval: request quota increase in Console, takes <1 hr to approve for modest asks.

## What this session actually demonstrated

The trust break from 2026-05-01 had a useful aftershock: this session, before deploying a single change, I called advisor and got the "audit casualty scope first" framing. That probably saved 30+ min — without the audit step I would have restored the guide doc, run TC-082 once, and called it done. Instead the audit found the lost doc was *single-file* scope, the guide is YouTube-sourced (legitimate provenance), and the restoration plan was clear before any deploy.

The Vertex pivot also demonstrated the value of `! gcloud ...` interactive commands — Ming did the browser login steps, I drove the non-interactive parts (project set, API enable, SA key scp + mount + container rebuild). Clean handoff between human and agent.
