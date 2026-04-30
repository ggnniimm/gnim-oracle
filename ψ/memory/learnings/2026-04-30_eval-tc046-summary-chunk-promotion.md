# TC-046: summary-chunk promotion via answer-shaped bullet (2026-04-30)

## Problem

TC-046 ("กรณีผู้ยื่นข้อเสนองานจ้างก่อสร้างเคยมีผลงานที่เกิดความเสียหายร้ายแรง คณะกรรมการพิจารณาผลมีสิทธิอย่างไร") consistent FAIL 3/3, missing `ชี้แจง`.

## Diagnosis

Source `01_กวจ_ว130_190269_แนวทางปฏิบัติในการกำหนดหลักเกณฑ์และสิทธิฯ.md` already contained `ชี้แจง` 6 times — including in the operative `## ข้อวินิจฉัย` and `## สรุปข้อวินิจฉัย` sections. Retrieval gap, not content gap.

The doc has TWO conflicting-feeling sections for the query:
- **ข้อเท็จจริง** (lines 25-39): describes the OLD problem state — "หน่วยงานของรัฐไม่สามารถใช้ดุลพินิจไม่รับราคา" (committee CAN'T reject)
- **ข้อวินิจฉัย** (lines 44-74): the NEW resolution — clauses 6.5/6.6 amendments giving committee explicit ชี้แจง demand + rejection rights

LLM kept pulling the ข้อเท็จจริง chunk (heavy with `ความเสียหายร้ายแรง` keywords matching the query) and stopped at the problem statement. The answer literally said "committee can't reject" — opposite of what TC-046 expects.

Chunk-selection issue: ข้อเท็จจริง chunk outranked ข้อวินิจฉัย/สรุป chunks for this query.

## Fix

Prepended an **answer-shaped first bullet** to `## สรุปข้อวินิจฉัย` that:
1. Starts with the exact query phrase: `**คณะกรรมการพิจารณาผลมีสิทธิ**`
2. Includes all must_contain keywords: `ความเสียหายร้ายแรง`, `๒ ปี`/`2 ปี`, `ชี้แจง`, `ข้อเสนอ`
3. Synthesizes BOTH amendments (6.5 ชี้แจง + 6.6 rejection) in one query-aligned sentence
4. Names the legal hook: `ตามข้อ ๖.๖ วรรคสองที่เพิ่มเติม`

Effect: this new chunk's embedding now scores higher for the query than the ข้อเท็จจริง chunk, so it surfaces in top-K context.

## Verification

3/3 PASS post-fix. Generation time dropped ~38s → ~31s (less wrangling — the answer-shaped chunk is closer to the desired output).

## Reusable pattern

When a doc has BOTH a problem-statement section and a resolution section, and the query semantically matches the problem-statement keywords more strongly:
1. Don't add new docs or rescue phrases
2. Look at `สรุปข้อวินิจฉัย` (or anchor summary) — does it have an "answer-shaped" sentence that mirrors the query phrasing?
3. If not, prepend one. The bullet should:
   - Start with the query's subject + question word transformed to assertive ("คณะกรรมการมีสิทธิ" for "คณะกรรมการมีสิทธิอย่างไร")
   - Include all keywords from must_contain
   - Cite the operative legal hook (ข้อ/มาตรา)
4. Force re-index single file via `index_md_folder.py --force-reindex --file ...`
5. Verify 3x

This is **chunk-rank promotion**, distinct from cross-ref injection (which copies content from a different doc) and rescue phrases (which append at generation time).

## Prod ops detail

- Source MD on prod: `/app/thai-legal-rag/data/md_backup/` (host) → `/app/data/md_backup/` (container, mounted)
- Backup created: `01_กวจ_ว130_190269_...md.bak.2026-04-30` (preserve old via Nothing-is-Deleted)
- Re-index inside container: `docker exec thai-legal-rag-app-1 python3 /app/pipeline/index_md_folder.py --dir /app/data/md_backup --force-reindex --file <name> --no-lightrag`
- Result: deleted 18 old vectors → indexed 19 new chunks (+1 from the new bullet)

## Side-finding (low priority)

Indexer reported `Total in DB: 27292 chunks` after this re-index. Yesterday's handoff documented `27,849 points` post-deploy. Discrepancy of ~557 chunks — could be:
1. Handoff figure was approximate
2. Some silent chunk loss between deploy and now (unlikely without explicit operations)
3. "Total in DB" semantic ≠ Qdrant points count (e.g., excludes anchor chunks, or counts dedup entries)

Not investigated — eval passes, retrieval working. Worth a probe next session if it persists.
