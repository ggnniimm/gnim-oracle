---
name: Qdrant payload vs MD file state divergence
description: MD files and Qdrant payloads can diverge — always verify both separately, especially for files that patch_from_drive.py cannot match by filename
type: project
---

When patching Drive file_ids in Thai Legal RAG, two separate stores need to be verified independently:

1. **MD files** (`data/md_backup/*.md`) — frontmatter `file_id` / `file_url`
2. **Qdrant payloads** — `file_id` / `file_url` fields per point

`patch_from_drive.py` only patches Qdrant for points whose `original_filename` stem matches a Drive mapping key (exact or fuzzy via `+`→`_`). Files with significantly different names between MD and Drive are left in "not in mapping" — their Qdrant payloads are NOT updated even if their MD was patched directly.

**Why:** Script uses filename-based lookup; manual patches bypass this. Qdrant can silently retain stale file_ids.

**How to apply:** After any patch session, spot-check Qdrant payload for the "not in mapping" set. Compare `file_id` in Qdrant against MD. If different, patch Qdrant directly using exact `original_filename` stem match.

## Bonus: `-N` suffix files

Files like `พรบ+...-2.md` (split PDFs page 2+) have no matching Drive entry. They should inherit the base document's file_id (strip `-N`, look up base). `patch_from_drive.py` currently has no logic for this — must be done manually or add fallback strip logic.
