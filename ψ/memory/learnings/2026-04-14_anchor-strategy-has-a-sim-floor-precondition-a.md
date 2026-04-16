---
title: ## Anchor Strategy Has a Sim Floor Precondition
tags: [retrieval-anchor, sim-score, embedding-dilution, must-contain, eval-design]
created: 2026-04-14
source: Thai Legal RAG TC-003 × กวจ. 20140 2026-02-26
---

# ## Anchor Strategy Has a Sim Floor Precondition

## Anchor Strategy Has a Sim Floor Precondition

Anchor strategy only works when the anchor chunk can outrank ALL other chunks in that document. If the document already has a high-sim chunk (title/header), the anchor will never be retrieved.

**Check before anchor engineering**:
```python
# Check sim scores for ALL chunks of target document
for i, meta in enumerate(store._metadata):
    if 'DOC_NUMBER' in meta.get('source_name', ''):
        v = store._index.reconstruct(i)
        sim = float(np.dot(qv, v))
        print(f'idx={i} sim={sim:.4f} | {meta["text"][:80]}')
```
If any existing chunk has sim > 0.80, adding a new anchor section will not help.

**Dilution effect**: Adding non-query-relevant content to an existing high-sim chunk LOWERS its sim score. Embedding models compute a single vector for full text.

**When anchor fails** (existing chunk sim > 0.80): Create a new TC with query specifically targeting that document/phrase. Don't force phrase into TC that asks a broader question.

**Rule**: must_contain phrases must be semantically predictable from the query, not just factually present in retrieved documents.

---
*Added via Oracle Learn*
