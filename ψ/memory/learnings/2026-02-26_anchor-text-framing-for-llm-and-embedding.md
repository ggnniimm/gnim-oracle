# Anchor Text Framing: LLM Structure and Embedding Similarity Are Aligned

**Date**: 2026-02-26
**Source**: thai-legal-rag — กวจ. 38381 embedding gap fix
**Tags**: retrieval-anchor, embedding, LLM-generation, RAG, framing

---

## Pattern

When adding a Retrieval Anchor to bridge an embedding gap, the text structure affects **both** the LLM's interpretation AND the embedding similarity. These two goals are more aligned than they appear.

---

## Discovery

Query: "คณะกรรมการตรวจรับพัสดุมีหน้าที่อะไรบ้าง"

The สรุปข้อวินิจฉัย chunk (sim=0.7307) was below FAISS_TOP_K=40. A retrieval anchor was added, but the LLM kept summarizing the 4 cases away.

**Wrong structure** (LLM ignores enumeration):
```
คณะกรรมการตรวจรับพัสดุ ไม่มีอำนาจสั่งการ ครอบคลุม: แก้ไขสัญญา ขยายระยะเวลา งดลดค่าปรับ บอกเลิกสัญญา
```
→ LLM reads: "there's a constraint, and these 4 things are examples of what the constraint covers" → summarizes to "ไม่มีอำนาจสั่งการ"

**Right structure** (LLM lists all):
```
คณะกรรมการตรวจรับพัสดุมีหน้าที่ 2 ประเภท: (1) ตรวจรับพัสดุ ตามข้อ 175/176 (2) เสนอความเห็น กรณีแก้ไขสัญญา ขยายระยะเวลา งดลดค่าปรับ บอกเลิกสัญญา (ไม่มีอำนาจสั่งการ)
```
→ LLM reads: "there are 2 types of duties, here they are" → enumerates all 4 cases ✓

---

## The Alignment Bonus

Moving "ไม่มีอำนาจสั่งการ" from front to end (parenthetical) also improved embedding similarity:
- Before: sim=0.8028 (constraint frames the sentence)
- After: sim=0.8136 (duty enumeration frames the sentence)

**Why**: Embedding models encode semantic frame. Constraint-first = "this is about limits". Duty-first = "this is about responsibilities". The query "มีหน้าที่อะไรบ้าง" is about responsibilities, so duty-first anchors score higher.

---

## Rules for Writing Retrieval Anchors

1. **Lead with the positive assertion**, not the exception/constraint
2. **Use explicit enumeration structure**: "มี X ประเภท: (1)... (2)..." signals to LLM that items are primary, not footnotes
3. **Put constraints at end as parentheticals**: "(ไม่มีอำนาจสั่งการ)" after the duties, not before
4. **System prompt can't override structure problems**: Adding "ให้แสดงครบทุกรายการ" doesn't help if the text structure already signals "these are footnotes"

---

## Secondary Lesson: Read Internal APIs Before Scripting

When writing one-off scripts that touch internal class attributes/methods:
- Read the source file first, note: attribute names, method signatures, kwarg names
- The 4-cycle AttributeError/ModuleNotFoundError pattern is entirely preventable

Common FAISS store gotchas in this codebase:
- Module: `src.indexing.faiss_store` (not `src.retrieval.faiss_store`)
- Attribute: `_metadata` (not `metadata`)
- Method: `save()` (not `_save()`)
- Search kwarg: `k=` (not `top_k=`)
