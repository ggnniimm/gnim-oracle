# Source-of-truth for thai-legal-rag MDs is `gnim-oracle-qdrant`, not `gnim-oracle` (2026-04-30)

> ⚠️ **SUPERSEDED 2026-04-30 afternoon** by `2026-04-30_corpus-resync-and-tc044-tc050-fixes.md`.
> The corpus resync that same day copied the canonical 1,385 MDs from `gnim-oracle-qdrant` INTO `gnim-oracle/.../md_backup/` and re-indexed prod from there. **Canonical is now `gnim-oracle/.../md_backup/`** (this repo). The qdrant repo's `lab/.../md_backup/` no longer exists; old MDs live at `gnim-oracle-qdrant/ψ/archive/data_with_ac/md_backup/` as a frozen snapshot (mtime 2026-03-16, do not edit). The TL;DR below was true at time of writing (morning of 04-30) but has been false since that afternoon. Verified by file_id set comparison vs prod Qdrant on 2026-05-09: every file_id in `gnim-oracle/.../md_backup/` is in prod (1,385/1,385); only 862/1,115 of qdrant-archive's file_ids are in prod, with 253 orphans.

## TL;DR (HISTORICAL — see superseding banner above)

For thai-legal-rag work, **always edit `gnim-oracle-qdrant/ψ/lab/thai-legal-rag/data/md_backup/`**. The `gnim-oracle/...` copy in this current repo is **outdated by 152 files (the entire AC folder of court judgments) and has 96% stale `file_id`s** that 404 on Drive.

## How to verify

```bash
# Compare counts
ls /Users/mingsaksaengwilaipon/gnim-oracle-qdrant/ψ/lab/thai-legal-rag/data/md_backup/*.md | wc -l   # 1,385 ← source-of-truth
ls /Users/mingsaksaengwilaipon/gnim-oracle/ψ/lab/thai-legal-rag/data/md_backup/*.md | wc -l         # 1,233 ← outdated

# Count ref_* (court judgments)
ls /Users/mingsaksaengwilaipon/gnim-oracle-qdrant/ψ/lab/thai-legal-rag/data/md_backup/ref_*.md | wc -l   # 152 ✓
ls /Users/mingsaksaengwilaipon/gnim-oracle/ψ/lab/thai-legal-rag/data/md_backup/ref_*.md | wc -l         # 0
```

## How this happened (best reconstruction)

- Ming has been working in `gnim-oracle-qdrant` since at least Mar 16. That's where MD link-fixes, AC court judgments, and frontmatter file_id updates have been accumulating.
- The 04-29 Drive ID remap deploy used `gnim-oracle/...` as source — wrong repo. Prod ended up with stale data.
- /recap and other automation use `cwd = gnim-oracle/` which biases the LLM toward thinking this is the working repo.
- MEMORY.md hinted at this (`/Users/mingsaksaengwilaipon/gnim-oracle-qdrant/.env` was referenced for Gemini API key) but the implication wasn't followed up.

## How to detect drift quickly

If working on a doc in `gnim-oracle/`, sanity-check:

1. Does the doc's `file_id` match the canonical Drive mapping?
2. Does the same filename exist in `gnim-oracle-qdrant/`?
3. Is `gnim-oracle-qdrant/`'s version newer (mtime)?

If any of these reveal a mismatch, **stop**. Switch to `gnim-oracle-qdrant`.

## Verification on a single doc (template)

```bash
F="01_กวจ_ว130_190269_..."
# this repo (outdated)
grep "^file_id" "ψ/lab/thai-legal-rag/data/md_backup/$F.md"
# sibling repo (canonical)
grep "^file_id" "/Users/mingsaksaengwilaipon/gnim-oracle-qdrant/ψ/lab/thai-legal-rag/data/md_backup/$F.md"
# Drive mapping (test what should be there)
# (drive_mapping.json on prod /tmp/drive_mapping.json)
```

If all three agree → safe. If `gnim-oracle/` differs from the other two → use the sibling.

## Implication for force-reindex

Any `index_md_folder.py --force-reindex --file <X.md>` reads frontmatter from disk and writes payload to Qdrant. If the disk MD has stale `file_id`, Qdrant gets stale `file_id`. **Never force-reindex without first verifying the source MD's `file_id` matches Drive canonical.**

Today's TC-046/051/071 reindexes did exactly this and reinforced the broken state on prod for those 3 docs.

## Action for next session

Before any work on thai-legal-rag MDs:
1. Confirm with Ming that `gnim-oracle-qdrant` is the right place (or migrate to a single canonical repo).
2. If staying with two repos, add a hard guard: refuse to edit `gnim-oracle/.../md_backup/*.md` and redirect to sibling.
3. Re-deploy prod from `gnim-oracle-qdrant` (1,385 files) to fix the user-visible link rot.
