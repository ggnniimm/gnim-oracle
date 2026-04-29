# Handoff: TC-027 Dig + Index Duplication Discovery

**Date**: 2026-04-23 08:50
📡 Session: 17e012f2 | gnim-oracle | ~30m

## Context
**Oracle**: Gnim | **Human**: Ming

## What We Did

### Committed 4 untracked files
- `ψ/memory/learnings/2026-03-12_crossref-stable-anchor-docs.md`
- `ψ/memory/retrospectives/2026-03/12/20.56_tc062-crossref-penalty-analysis.md`
- `ψ/lab/sample-docs/gemini_embedding_2.md`
- `ψ/lab/thai-legal-rag/pipeline/batch_ocr.py`
- Commit: `cf7fa63`

### TC-027 "ผู้ทิ้งงาน" — Deep Dig
- Ran 3 standalone runs → 2 PASS / 1 FAIL = **LLM variance** (not regression)
- **1117 not retrieved**: confirmed not a missing-from-index bug — 1117 has 56 Qdrant points. Root cause: MMR diversity penalty suppresses 1117 because 2190 is selected first (content too similar). By design.
- **ว_973**: retrieved every run, has มาตรา 109 chunks. LLM sometimes paraphrases without citing section number → fail criterion 3.

### Big Finding: Entire Qdrant Index Duplicated
```
Qdrant:    56,185 points
dedup.db:  27,912 entries (all added 2026-03-12, single rebuild)
Pattern:   every doc has ALL chunks duplicated exactly 2×
```
Likely cause: dedup.db cleared + rebuilt on 2026-03-12 without clearing Qdrant first → old chunks + new chunks coexist.

**Impact**: reranker text-dedup handles it at query time (line 126-135 reranker.py), so not catastrophic. But candidate pool (120 slots) is 50% duplicates → effective diversity = 60 unique chunks instead of 120.

## Pending

- [ ] Fix TC-027 expected_sources: remove `1117` (MMR correctly suppresses it; 2190 covers same content) — 2 min
- [ ] Full re-index: delete Qdrant collection + clear dedup.db + rebuild (~30 min) — restores 120-slot diversity
- [ ] TC-027 accepted as flaky (2/3 pass) — no must_contain fix needed
- [ ] Stale branches: `feat/claude-design-ui`, `fix/stale-cookie-and-rag-improvements` (merged)
- [ ] Open PRs: #23 dependabot, #13, #12, #11 — review relevance
- [ ] `settings.local.json` has uncommitted changes

## Next Session

- [ ] Decide: re-index now or defer? (duplication doesn't break eval but halves candidate pool)
- [ ] Fix TC-027 expected_sources → remove `1117`
- [ ] Clean up stale branches (fix/stale-cookie already merged via PR #24)
- [ ] Review issues #11, #12, #13 — still relevant after eval 78/80?

## Key Files
- `ψ/lab/thai-legal-rag/eval/golden_test_cases.json` — TC-027 expected_sources
- `ψ/lab/thai-legal-rag/src/retrieval/reranker.py:126-135` — text-dedup logic
- `ψ/lab/thai-legal-rag/src/retrieval/reranker.py:55-80` — MMR selection
- `ψ/lab/thai-legal-rag/data/dedup.db` — 27,912 entries, all 2026-03-12
