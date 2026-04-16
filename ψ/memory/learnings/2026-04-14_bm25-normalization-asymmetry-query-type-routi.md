---
title: ## BM25 Normalization Asymmetry & Query-Type Routing
tags: [bm25, faiss, normalization, query-routing, retrieval]
created: 2026-04-14
source: Thai Legal RAG retrieval debugging 2026-02-25
---

# ## BM25 Normalization Asymmetry & Query-Type Routing

## BM25 Normalization Asymmetry & Query-Type Routing

When fusing multiple retrieval sources with normalized scores + weights, the source with the highest weight always wins ties — even if a lower-weight source has a perfect exact match. BM25 (weight 0.9) can never beat FAISS (weight 1.0) in final ranking.

**Fix — route by query type**:
| Query type | Best source | Detection |
|---|---|---|
| Bare number (doc ID) | BM25 only | `\b\d{4,}\b` |
| Provision reference | BM25 primary | มาตรา, ข้อ, วรรค |
| Semantic concept | FAISS + BM25 | General |

**BM25Store internal structure**:
```python
bm25._corpus = [_tokenize(m['text']) for m in meta]  # CORRECT
bm25._rebuild()  # rebuilds BM25Okapi from _corpus
# save() pickles {"corpus": self._corpus, "metadata": self._metadata}
```

**Config/code drift warning**: Always import shared constants from config — never hardcode weights in individual modules.

---
*Added via Oracle Learn*
