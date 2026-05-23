---
name: ocr-thai-digit-2425-confusion
description: gemini-2.5-pro OCR misreads Thai digit ๒๔ → ๒๕ in doc-number position, breaks ว-number search
metadata:
  type: project
---

# OCR Thai digit ๒๔ → ๒๕ confusion (gemini-2.5-pro)

**Observed 2026-05-22**: 2 May-2026 OCR'd MDs had doc_number `"เลขที่ ว ๒๕๒"` despite filename = `ว242` and Drive PDF title also = `ว242`. Both were OCR'd by `ocr_engine: gemini-2.5-pro` (dates 2026-05-15 + 2026-05-17). Ming visually confirmed: PDF says ว ๒๔๒, OCR mis-fired ๒๔ → ๒๕.

**Affected files**:
- `กค+(กวจ)+0405.2-ว242.md` (file_id `1yuXKX-ptWo_zxM_gG78ddK8D33YSUe82`, BE 2561, ยาเสพติด)
- `01_กวจ_ว242_080469_แนวทางปฏิบัติเกี่ยวกับการดำเนินการจัดซื้อจัดจ้างฯ.md` (file_id `10c8Fxtn1Psv6lWhxSeeSAqNeOSkGKiTb`, BE 2569, ตะวันออกกลาง)

Both fixed by editing `doc_number` + anchor line: `ว ๒๕๒` → `ว ๒๔๒`, then `--force-reindex` (17 + 25 = 42 chunks).

**Why this matters for retrieval**: RAG searches embedding + BM25 of payload `text` — not filename. When OCR puts ว ๒๕๒ everywhere in body/anchor and user queries "ว 242", neither embedding nor token match fires. Query returns "not found" even though the doc is fully indexed under correct file_id.

**How to apply**:
1. **Symptom**: user reports "ถามว่ามี ว XXX มั๊ย ตอบไม่พบ" → run `grep -l "ว ๒X${last_digit_alt}" md_backup/` on the adjacent Thai digit (๒↔๓, ๔↔๕, ๖↔๘) to surface OCR drift
2. **Pre-deploy audit**: after batch OCR with gemini-2.5-pro, sanity-check that `filename ว-number` matches `doc_number ว-number` for each new MD before reindex
3. **Authority order when verifying**: (a) Ming-named filename > (b) Drive PDF title > (c) gemini-2.5-pro OCR output > (d) Google Drive native OCR (worst — `read_file_content` shows ๒๔/๒๕ alternating within same doc, unreliable for digit verification)

**Why filename = source of truth**: Ming names files manually after visually reading the PDF first; OCR runs blind. See [[md-filename-must-match-drive]].

Related: [[verify-before-act]], [[local-first-prod-runtime-only]].
