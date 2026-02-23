# Lesson: Thai Legal RAG — Knowledge Quality & Superseded Documents

**Date**: 2026-02-23
**Source**: thai-legal-rag evaluation session

## Pattern 1: "ผู้มีอำนาจ" in พ.ร.บ. จัดซื้อจัดจ้าง is defined by the ระเบียบ

ม.97, ม.102, ม.103 all use "ให้อยู่ในดุลพินิจของผู้มีอำนาจ" — but the implementing ระเบียบ defines different people:
- **ม.97 (แก้ไขสัญญา)** → ระเบียบ ข้อ 165 วรรคสาม = ผู้มีอำนาจอนุมัติสั่งซื้อหรือสั่งจ้าง (approval) + หัวหน้าหน่วยงาน (signing)
- **ม.102 (งดลดค่าปรับ/ขยายเวลา)** → ระเบียบ ข้อ 182 = หัวหน้าหน่วยงานของรัฐ
- **ม.103 (บอกเลิกสัญญา)** → หัวหน้าหน่วยงานของรัฐ

ว 476 (30 ก.ย. 2562) confirmed: "การแก้ไขสัญญาไม่ว่ากรณีใด ย่อมต้องได้รับอนุมัติจากผู้มีอำนาจอนุมัติสั่งซื้อหรือสั่งจ้าง"

## Pattern 2: หนังสือเวียน ซ้อมความเข้าใจ supersedes conflicting หนังสือวินิจฉัย

กวจ ๐๕๒๓ (2560) said: แก้ไขสัญญาที่ไม่เพิ่มวงเงิน → หัวหน้าหน่วยงานของรัฐ
ว 476 (2562) corrected: **ไม่ว่ากรณีใด** → ผู้มีอำนาจสั่งซื้อสั่งจ้าง

A ว ซ้อมความเข้าใจ is issued precisely because existing interpretations were inconsistent. It is authoritative re-statement, not commentary. Later กวจ responses (๒๖๑๔๑, ๘๔๑๐) all cite ว 476, not กวจ ๐๕๒๓.

**กวจ ๐๕๒๓ ม.97 interpretation: DO NOT CITE** (superseded by ว 476)
**กวจ ๐๕๒๓ ม.102 interpretation: still valid**

## Pattern 3: Superseded Note — RAG Knowledge Correction Without Re-embedding

To prevent a RAG document from being cited on a specific topic, add a blockquote warning to the document text. LLMs see the warning in-context and know to discard it.

```markdown
> **หมายเหตุ (Superseded):** ข้อวินิจฉัยในส่วนที่เกี่ยวกับ **มาตรา ๙๗** ถูก supersede โดย ว ๔๗๖ (๓๐ ก.ย. ๒๕๖๒)...
```

Steps:
1. Edit MD backup file → add note after title heading
2. Re-parse with `load_md_file()` → new chunks with note in text
3. Patch existing metadata.pkl/bm25.pkl chunks: append note to `text` field
4. No re-embedding needed (Option A) — just metadata text update

Limitation: chunks still retrieved, LLM must decide to discard. For hard suppression, use metadata filter (Option B).

## Pattern 4: Manager.add_batch() Always Appends

`IndexManager.add_batch()` has no replace/delete. If you load the manager, manually filter metadata.pkl, then call add_batch, the manager uses its in-memory state (original), not the filtered disk state. Result: duplicates.

Safe re-index pattern:
```python
# WRONG: filter disk then add → duplicates
meta_filtered = [...filter...]
meta_path.write_bytes(pickle.dumps(meta_filtered))  # saved to disk
mgr.add_batch(...)  # uses in-memory original!

# RIGHT: patch existing chunks' text instead
for d in meta:
    if should_update(d):
        d['text'] += note
meta_path.write_bytes(pickle.dumps(meta))
```

## Context: Thai Legal Document Hierarchy

```
พ.ร.บ. (กฎหมายแม่บท)
  └── ระเบียบกระทรวงการคลัง (implementing rules, define "ผู้มีอำนาจ")
        └── หนังสือเวียน ว (ซ้อมความเข้าใจ — authoritative clarification)
              └── หนังสือวินิจฉัย กวจ (case-by-case interpretation)
```

หนังสือเวียนที่ออกทีหลัง > หนังสือวินิจฉัยที่ออกก่อน
