---
title: Qdrant payload and MD files are TWO separate stores that can diverge silently.
tags: [qdrant, thai-legal-rag, drive-patch, data-consistency, file-id]
created: 2026-04-14
source: rrr: gnim-oracle-qdrant
---

# Qdrant payload and MD files are TWO separate stores that can diverge silently.

Qdrant payload and MD files are TWO separate stores that can diverge silently.

`patch_from_drive.py` only patches Qdrant for points whose `original_filename` stem matches a Drive mapping key (exact or fuzzy). Files with significantly different names between MD and Drive end up in "not in mapping" — their Qdrant payloads are NOT updated even when their MD was patched directly earlier.

Verification rule: After any patch session, spot-check Qdrant payload for "not in mapping" files. Compare `file_id` in Qdrant vs MD. If different, patch Qdrant directly using exact `original_filename` stem match.

Bonus: `-N` suffix files (split PDFs, e.g. `พรบ+...-2.md`) have no Drive entry. They should inherit the base document's file_id (strip `-N`, look up base). Currently must be done manually.

---
*Added via Oracle Learn*
