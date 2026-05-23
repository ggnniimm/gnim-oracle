---
name: specific-query-drops-vector-statute-buried
description: "is_specific_query() drops vector hits for มาตรา/วรรค/ข้อ/หมวด queries, but BM25 buries statute chunks under doc-ID noise — statute lookup fails"
metadata:
  type: project
---

# `is_specific_query` drops vector → BM25 buries statute chunk

**Observed 2026-05-23**: Query `"ม.103 วรรคสาม คืออะไร"` on prod RAG returned vague paraphrase with [4] citing ว 409 (รหัสวัสดุก่อสร้าง — "ม. 103" = sqm of รื้อกอง), NOT the statute chunk that contains the literal text of มาตรา ๑๐๓.

**Statute chunk IS indexed**:
- file_id `1raRAyQai8gybh1jaHaoHCSF-E797gISF` = `พรบ+จัดซื้อจัดจ้าง+...2560-2.pdf`
- 120 chunks total, 1 chunk has literal `มาตรา ๑๐๓` text
- chunk header: `[พ.ร.บ.จัดซื้อจัดจ้างฯ 2560 | มาตรา 103]`

**Why retrieval misses it** — instrumentation showed:

| Query | vector hits | bm25 hits | ม.๑๐๓ chunk rank (vector / bm25 / reranked) |
|---|---:|---:|---|
| `ม.103 วรรคสาม คืออะไร` | **0** | 30 | None / None / None |
| `มาตรา ๑๐๓ วรรคสาม` | **0** | 24 | None / None / None |
| `มาตรา 103 พ.ร.บ.จัดซื้อ` | **0** | 23 | None / None / None |
| `ม.103` (bare) | 366 (with expand) | 194 | rank 72 vector / None bm25 / 28/29 reranked |

**Root cause** — `src/retrieval/retriever.py` line ~107:
```python
if specific:
    # For ID/provision lookups, BM25 exact match is authoritative.
    # Vector embeddings of bare numbers return generic semantic matches that add noise.
    return {"vector": [], "bm25": list(merged_bm25.values())}
```

`is_specific_query()` patterns in `src/retrieval/query_expand.py:30-38`:
- `วรรค\s*(หนึ่ง|สอง|สาม|สี่|ห้า|\d+)` → matches "วรรคสาม" anywhere
- `มาตรา\s*[\d๐-๙]+` → matches "มาตรา ๑๐๓"
- `ข้อ`, `หมวด`, 4+ digit doc IDs → same lane

When a query matches any pattern, **vector retrieval is dropped entirely** — by design (assumption: BM25 exact-match is more authoritative for provision lookups).

**Why the assumption breaks for statute queries**:
1. BM25 token "103" appears in dozens of unrelated docs (material codes, sqm prefixes, ระเบียบ ข้อ 103, ฯลฯ) → ม.๑๐๓ chunk pushed below top-30
2. Query "ม.103" (Arabic-dotted) ≠ statute chunk's "มาตรา ๑๐๓" (Thai numerals) surface — BM25 lemma overlap weak
3. Statute MD chunk lacks distinguishing Thai-numeral phrase match for "วรรคสาม"

**Design hole**: "specific → BM25 only" was sized for **doc-ID lookups** (4+ digit) where BM25 precision is naturally high (`23097` is rare). It fails for **statutory provision lookups** (`มาตรา X`, `ข้อ Y`) where the section number is a common 1-3 digit token reused across the corpus.

**How to apply** (fix candidates — pick one when prioritizing):

1. **Carve-out the statute file**: in retriever.py, when `specific` AND query matches `มาตรา|ข้อ|หมวด`, do `vector_search(filter=file_id IN statute_set, top_k=3)` AND keep BM25 — both lanes. Statute set = 2 file_ids (พ.ร.บ. + ระเบียบ).
2. **Glossary expand**: add `"ม.X" → "มาตรา X"`, `"มาตรา X" → "มาตรา X (in Thai numerals)"` to glossary so BM25 surface forms align.
3. **Hybrid threshold**: keep top-3 vector hits even when `specific`, only down-weight (not zero) — preserves recall safety net.

**How to test the fix**: query "ม.103 วรรคสาม คืออะไร" must place statute chunk in top-5 ranked. Add as eval TC alongside existing 84-TC suite.

Related: [[verify-before-act]], [[query-store-before-filter]], [[must-contain-answer-direction]].
