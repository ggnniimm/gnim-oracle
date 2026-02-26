# Lesson: Anchor Strategy Has a Sim Floor Precondition

**Date**: 2026-02-26
**Source**: thai-legal-rag TC-003 × กวจ. 20140 session

## Pattern

Anchor strategy (## บทสรุปสำหรับสืบค้น) only works when the anchor chunk can **outrank all other chunks in that document**. If the document already has a high-sim chunk (title/header), the anchor will never be retrieved.

**Before starting anchor engineering, always run:**
```python
# Check sim scores for ALL chunks of target document
for i, meta in enumerate(store._metadata):
    if 'DOC_NUMBER' in meta.get('source_name', ''):
        v = store._index.reconstruct(i)
        sim = float(np.dot(qv, v))
        print(f'idx={i} sim={sim:.4f} | {meta["text"][:80]}')
```

If any existing chunk already has sim > 0.80, adding a new anchor section will not help.

## Failure Mode Observed

กวจ. 20140:
- Chunk บทนำ (title): sim=0.8149 → high because title contains exact query terms
- Anchor v1 (บทสรุป): sim=0.7674 → lower
- Anchor v2 (บทสรุป revised): sim=0.7553 → even lower

Result: MMR/top-K always picks chunk บทนำ, anchor never retrieved, LLM never sees anchor text.

## Dilution Effect

Adding non-query-relevant content to an existing high-sim chunk LOWERS its sim score:
- Chunk 32193 original: sim=0.8149 (title only)
- Chunk 32193 after appending paragraph: sim=0.7659 (title + "แผน" paragraph)
- Net: 20140 disappeared from retrieval entirely

**Embedding models compute a single vector for full text. Off-topic appends dilute semantic signal.**

## When Anchor Strategy Works vs Fails

| Condition | Outcome |
|-----------|---------|
| Document has no high-sim chunk for query | Anchor section can win → use it |
| Document has title/header that matches query well | Anchor will lose → different approach needed |
| Existing chunk sim > 0.80 | Do NOT add anchor section, find another way |

## Right Fix When Document Already Has High-Sim Chunk

If you need phrase X to appear in LLM output but X comes from a document whose existing chunks already score high:
1. **Create a new TC** with a query specifically designed for that document/phrase
2. **Don't force phrase X into TC** that asks a broader question
3. The existing chunk will surface the document — but LLM will only include what the query naturally elicits

## must_contain ≠ document content

"แผน" is factually from 20140 but is an **edge case** (specific contract clause), not a general duty. TC-003 asks "หน้าที่ทั่วไป" → LLM answers with main duties from ระเบียบฯ 175/176. Adding edge-case phrases to must_contain of a general query will always be non-deterministic.

**Rule: must_contain phrases must be semantically predictable from the query, not just factually present in retrieved documents.**

## Tags

`retrieval-anchor`, `sim-score`, `embedding-dilution`, `must_contain`, `eval-design`, `precondition`
