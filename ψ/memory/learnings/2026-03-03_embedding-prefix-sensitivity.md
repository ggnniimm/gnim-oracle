# Embedding Prefix Sensitivity

**Date**: 2026-03-03
**Source**: rrr: thai-legal-rag metadata prefix experiment
**Tags**: #embedding #faiss #gemini #retrieval #rag

## Pattern

Adding metadata to chunk text before embedding can **hurt** retrieval if the metadata has low cardinality.

## Evidence

- Original prefix: `[ref_number | date | category]` → 44/44 eval
- V1 (+ topic + subtopic + laws_referenced): → 36/44 (-8 TCs)
- V2 (+ subtopic only): → 38/44 (-6 TCs)
- Reverted to original: → 44/44

## Why It Happens

1. **Prefix dominates embedding**: A 100-char prefix on a 400-char chunk = 25% of semantic signal is metadata
2. **Low cardinality = noise**: `topic` is "การจัดซื้อจัดจ้าง" for ~95% of docs — adds no discriminative power, just dilutes content signal
3. **Gemini embedding model sensitivity**: The model treats bracket-enclosed text as important context, so any change reshuffles all results

## Rule

Only prepend metadata that has **high cardinality** and **genuine discriminative power**:
- `ref_number` — unique per document
- `date` — varies across docs
- `category` — 3-5 distinct values (ข้อหารือ, หนังสือเวียน, กฎกระทรวง, etc.)

Do NOT prepend:
- `topic` — same for 95% of docs
- `laws_referenced` — too long (50-200 chars), dominates the chunk
- `subtopic` — marginal value, adds noise

## Corollary: must_contain keyword design

Use the **shortest natural form** that the LLM consistently generates:
- "ขยายเวลา" > "ขยายระยะเวลา" (LLM prefers short form)
- Avoid synonyms the LLM freely substitutes: "ไม่อาจ" ↔ "ไม่สามารถ"
