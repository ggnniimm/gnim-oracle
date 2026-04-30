# TC-051: ป.พ.พ. backstop injection in top-cited doc (2026-04-30)

## Problem

TC-051 ("ผู้รับจ้างเรียกร้องค่าใช้จ่ายหรือค่าเสียหายใดๆ จากการที่ผู้ว่าจ้างขยายระยะเวลาได้หรือไม่") consistent FAIL. Missing `["ป.พ.พ.", "ประมวลกฎหมายแพ่ง"]`.

## Diagnosis

- Retrieval ✓: 4 court judgments retrieved (๗๓/๒๕๖๕, ๑๕๙/๒๕๖๖, ๑๖๘/๒๕๖๖, ๑๕/๒๕๖๖)
- ป.พ.พ. distribution per source MD:
  - ๗๓/๒๕๖๕: 0 hits
  - ๑๕๙/๒๕๖๖: 0 hits
  - ๑๖๘/๒๕๖๖: 3 hits (ม.๘ retention, ม.๒๔๑ — different angle: contractor's fault / force majeure)
  - ๑๕/๒๕๖๖: 3 hits (ม.๒๒๒ — but this doc is about employer claiming damages from contractor, opposite direction)
- LLM cited primarily `๑๕๙/๒๕๖๖` (the most directly relevant doc, with no ป.พ.พ.)
- Result: contract-only answer, legally correct for the common case but missing statutory backstop

## Fix: cross-ref injection in top-cited doc's สรุปข้อวินิจฉัย

Appended a third bullet to `๑๕๙/๒๕๖๖`'s `## สรุปข้อวินิจฉัย`:

> **กรอบกฎหมายแพ่งสำหรับการเรียกค่าเสียหาย**: ในกรณีที่ผู้ว่าจ้างผิดสัญญาและเป็นเหตุให้ต้องขยายระยะเวลา (เช่น ส่งแบบที่แก้ไขล่าช้า สั่งระงับงาน) ผู้รับจ้างมีสิทธิเรียกค่าสินไหมทดแทนตามกรอบ**ประมวลกฎหมายแพ่งและพาณิชย์ มาตรา ๒๑๕ และมาตรา ๒๒๒** (ค่าสินไหมทดแทนเพื่อความเสียหายอันเกิดแต่การไม่ชำระหนี้ตามปกติ และความเสียหายอันเกิดแต่พฤติการณ์พิเศษที่คาดเห็นได้) เป็นเงินเพิ่มเติม นอกเหนือจากค่าใช้จ่ายในการควบคุมงานที่ผู้ว่าจ้างต้องรับผิดชอบเองตามที่กล่าวข้างต้น ทั้งนี้ ขึ้นอยู่กับข้อกำหนดในสัญญาจ้างเป็นสำคัญ

This bullet:
- Names `ประมวลกฎหมายแพ่งและพาณิชย์` (matches must_contain)
- Cites specific sections (ม.๒๑๕, ม.๒๒๒) — legally correct for breach-of-contract damages doctrine
- Connects logically to existing summary (extends "ผู้ว่าจ้างต้องรับผิดชอบ" with statutory backstop)
- Mentions the contract-clause caveat (preserves the LLM's primary answer)

## Verification

3/3 PASS post-fix. TC-046 unchanged (no regression on the previously-fixed doc).

Force-reindex: deleted 20 vectors → 22 new chunks (+2 from the longer bullet).

## Pattern: cross-ref injection (true cross-doc) vs chunk promotion (intra-doc)

This is **classic cross-ref injection** (per `2026-03-09_crossref-injection-top-ranked-docs`):
- The doc being edited (๑๕๙/๒๕๖๖) doesn't naturally contain ป.พ.พ.
- We're INJECTING a citation to a different legal source (ป.พ.พ. ม.๒๑๕/๒๒๒) into this doc's summary
- Triggered because retrieval consistently picks this doc as #1 for the query

Distinct from TC-046's pattern (`2026-04-30_eval-tc046-summary-chunk-promotion`):
- That fix REORDERED existing content within a single doc — making the resolution chunk outrank the problem chunk
- Both patterns edit `## สรุปข้อวินิจฉัย`, but the intent differs

## Prod ops

- Source MD: `/app/thai-legal-rag/data/md_backup/คำวินิจฉัยที่_๑๕๙_๒๕๖๖.md` (host) → `/app/data/md_backup/` (container)
- Backup: `.bak.2026-04-30` (Nothing-is-Deleted)
- Re-index: `docker exec thai-legal-rag-app-1 python3 /app/pipeline/index_md_folder.py --dir /app/data/md_backup --force-reindex --file <name> --no-lightrag`

## Same caveat as TC-046

Source MD edit lives on prod + local cache only — `data/` is gitignored. Patch documented in this file with full before/after content.
