---
date: 2026-03-12
source: "rrr: gnim-oracle"
concepts: ["cross-reference", "retrieval", "ว647", "stable anchor", "thai procurement law", "old framework mapping"]
---

# Cross-ref in Stable Anchor Documents > Individual คำวินิจฉัย

## Pattern

When a document has relevant content but can't be retrieved (keyword gap too wide), cross-referencing into a "stable anchor" document works better than cross-referencing into another คำวินิจฉัย.

## Why

- Individual คำวินิจฉัย retrieval varies by query — rank #1 for one query, absent for another
- Stable anchor documents like **ว647** are retrieved for almost any procurement query because they cover the full lifecycle
- Cross-ref in ว647 is practically guaranteed to reach the LLM context

## Example

คำวินิจฉัยที่ 4/2561 (ระเบียบ 2535 framework) has principle: "หักวันที่ไม่ต้องรับผิดก่อน แล้วค่อยดูว่าเกิน 10% หรือไม่"
- Cross-ref in 142/2566 → 142/2566 itself didn't get retrieved next run
- Cross-ref in ว647 (between งดลดค่าปรับ and บอกเลิกสัญญา sections) → content consistently appears in LLM answer

## Rule

**Prefer stable anchor docs for cross-ref over individual คำวินิจฉัย.**

Stable anchors in this corpus: ว647, ว52, พ.ร.บ. 2560, ระเบียบ 2560

## Old Framework Mapping

Documents under ระเบียบ 2535 use different terminology (ข้อ 131 vs มาตรา 103, ข้อ 139 vs มาตรา 102). They need keyword enrichment in สรุปข้อวินิจฉัย to be retrievable by modern-framework queries.
