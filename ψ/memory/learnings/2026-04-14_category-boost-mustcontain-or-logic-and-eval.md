---
title: ## Category Boost, must_contain OR Logic, and Eval Tool Parity
tags: [eval, must_contain, category-boost, rag, thai-legal-rag, reranker]
created: 2026-04-14
source: Oracle Learn
---

# ## Category Boost, must_contain OR Logic, and Eval Tool Parity

## Category Boost, must_contain OR Logic, and Eval Tool Parity

### Context
Thai Legal RAG — document priority (คำพิพากษา > กวจ.), must_contain OR logic gaps (2026-03-15/16).

### Pattern: Category Boost in Reranker
Legal RAG needs authority hierarchy in retrieval scores. `_CATEGORY_BOOST` dict in reranker applies after normalize:
```python
_CATEGORY_BOOST = {"ศาลปกครอง": 1.30, "สำนักงานอัยการสูงสุด": 1.05}
```
`category` field already exists in chunk metadata — no re-index needed. Legal reasoning should start from court judgments, not agency opinions.

### Pattern: must_contain Must Match Question Type
When writing `must_contain`, think: "would a correct answer to THIS EXACT QUESTION reliably contain this word?"
- "คืออะไร" (definitional) → use concept words, not consequence words
- "ผลเป็นอย่างไร" (consequence) → use action/outcome words
- Mismatch causes false failures even when LLM is answering correctly

### Pattern: OR Logic for Abbreviation/Full-Form Pairs
```json
"must_contain": [["ป.พ.พ.", "ประมวลกฎหมายแพ่ง"]]
```
Both run_eval.py AND export_answers_csv.py must support array-of-arrays — they had diverged, causing hidden inconsistency.

### Pattern: "False Pass" TC Detection
TC can pass must_contain via a DIFFERENT document than the intended expected_source. The answer is correct but the source quality is wrong. Treat as a separate severity: "pass-but-source-miss" vs "complete pass".

### Pattern: find_dotenv() Over load_dotenv() in Nested Projects
`load_dotenv()` with no args is brittle in projects with symlinks and nested directories. `load_dotenv(find_dotenv())` finds .env correctly regardless of CWD.

---
*Added via Oracle Learn*
