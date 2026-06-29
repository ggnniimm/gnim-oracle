---
name: qdrant-soft-delete-approximate-count
description: Qdrant approximate count inflates by soft-deleted vectors — always use exact=True for ground truth
metadata:
  type: feedback
---

`client.count(exact=False)` (default) includes soft-deleted vectors that haven't been compacted yet by the optimizer. Can overcount by 1,000–2,000+ in an active collection.

**Why:** Verified 2026-05-28 — approximate showed 36,644, exact showed 34,897 (before our 773 deletions). Difference of 1,747 was soft-deleted from prior operations.

**How to apply:** Always use `client.count(collection_name=col, exact=True)` when verifying chunk counts after deletions or re-indexing. The approximate count is fine for rough capacity planning but not for verifying correctness of operations.

After `exact=True` and `exact=False` agree, optimization has completed — the collection is stable.
