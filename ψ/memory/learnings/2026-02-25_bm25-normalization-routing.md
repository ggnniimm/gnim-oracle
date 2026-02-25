# Lesson: BM25 Normalization Asymmetry & Query-Type Routing

**Date**: 2026-02-25
**Source**: thai-legal-rag retrieval debugging

## Core Lesson

When fusing multiple retrieval sources with normalized scores + weights, the source with the highest weight **always wins ties** — even if a lower-weight source has a perfect exact match.

```
FAISS:  max_score=0.71 → normalized 1.0 × weight 1.0 = 1.0
BM25:   max_score=10.82 → normalized 1.0 × weight 0.9 = 0.9
```

Result: BM25 can never beat FAISS in final ranking, even for perfect exact matches.

## The Fix: Route by Query Type

Don't try to blend all sources for all queries. Route based on query type:

| Query type | Best source | Pattern |
|------------|-------------|---------|
| Bare number (doc ID) | BM25 only | `\b\d{4,}\b` |
| Provision reference | BM25 primary | `มาตรา`, `ข้อ`, `วรรค` |
| Semantic concept | FAISS + BM25 | General queries |

```python
# In is_specific_query():
r"\b\d{4,}\b",  # 4+ digit number = doc ID lookup

# In retriever:
if specific:
    return {"faiss": [], "bm25": list(merged_bm25.values()), "lightrag": []}
```

## BM25Store Internal Structure

```python
# _rebuild() uses self._corpus (list of tokenized lists)
bm25._corpus = [_tokenize(m['text']) for m in meta]  # CORRECT
bm25._docs = ...  # WRONG — attribute doesn't exist
bm25._rebuild()  # rebuilds BM25Okapi from _corpus
bm25.save()
```

`save()` pickles `{"corpus": self._corpus, "metadata": self._metadata}`.

## Config/Code Drift Warning

Always import shared constants from config — never hardcode them:

```python
# BAD: hardcoded in reranker, stale vs config
"bm25": 0.7

# GOOD: single source of truth
from src.config import BM25_WEIGHT
"bm25": BM25_WEIGHT
```

## Tags

bm25, faiss, reranker, normalization, query-routing, retrieval-quality, thai-legal-rag
