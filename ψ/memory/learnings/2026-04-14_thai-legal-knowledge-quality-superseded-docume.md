---
title: ## Thai Legal Knowledge Quality: Superseded Documents & Document Hierarchy
tags: [thai-legal, superseded, document-hierarchy, knowledge-quality, rag]
created: 2026-04-14
source: Thai Legal RAG evaluation session 2026-02-23
---

# ## Thai Legal Knowledge Quality: Superseded Documents & Document Hierarchy

## Thai Legal Knowledge Quality: Superseded Documents & Document Hierarchy

**Thai legal document hierarchy**:
```
พ.ร.บ. (กฎหมายแม่บท)
  └── ระเบียบกระทรวงการคลัง (implementing rules)
        └── หนังสือเวียน ว (ซ้อมความเข้าใจ — authoritative clarification)
              └── หนังสือวินิจฉัย กวจ (case-by-case interpretation)
```
หนังสือเวียนที่ออกทีหลัง > หนังสือวินิจฉัยที่ออกก่อน

**กวจ ๐๕๒๓ ม.97 interpretation: DO NOT CITE** — superseded by ว476 (2562). กวจ ๐๕๒๓ ม.102 interpretation: still valid.

**Superseded note technique** (RAG knowledge correction without re-embedding): Add blockquote warning to document MD file: `> **หมายเหตุ (Superseded):** ข้อวินิจฉัยในส่วนที่เกี่ยวกับ มาตรา ๙๗ ถูก supersede โดย ว๔๗๖...` — LLM sees it in-context and discards. No re-embedding needed.

**IndexManager.add_batch() always appends** — never use to replace. Patch existing chunks' text field instead.

---
*Added via Oracle Learn*
