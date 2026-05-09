# Gemini 2.5 Pro vs 2.5 Flash for verbatim OCR

**Date**: 2026-05-09
**Source**: gnim-oracle/thai-legal-rag — ว ๒๑๐ A/B test (Pro v1 vs Flash baseline)
**Confidence**: Medium — n=1 doc, but pattern is consistent with model behavior in general

## Pattern

For verbatim-faithful OCR of legal/government documents, **Pro is "smarter" than Flash in ways that hurt verbatim**. Default prompt that Flash follows literally, Pro interprets liberally:

| Behavior | Flash | Pro (without explicit rule) |
|---|---|---|
| Tables that look redundant with adjacent text | Keeps verbatim | **Drops** |
| Law refs with subsections (`มาตรา ๒๙ วรรคหนึ่ง (๔)`) | Keeps full | **Truncates** to `มาตรา ๒๙` |
| `quality_note` field | Empty when OCR is fine | **Hallucinates** content critique (e.g. "future date typo") |
| Doc identifier completeness | Often partial (`ว 210`) | Full (`ที่ กค (กวจ) ๐๔๐๕.๒/ว ๒๑๐`) |
| Sentence boundary preservation | Sometimes splits at section heading | Keeps as one |
| Indentation of nested items | Often flat | Properly nested |

**Net for legal corpus**: Without explicit anti-summarization rules, Pro is a wash — gains in structure offset by losses in faithfulness. With 3 explicit rules, Pro becomes net better.

## The 3 explicit rules that fix Pro

Added to `_EXTRACT_PROMPT_TEMPLATE` in `src/ingestion/ocr.py`:

```
- **ตารางทุกตารางในเอกสารต้องคงไว้ครบทุกตาราง** — แม้เนื้อหาในตารางจะดูซ้ำกับข้อความ
  ก่อนหน้า ก็ห้ามตัดทิ้ง ตารางคือส่วนของเอกสารต้นฉบับและต้องคัดลอก verbatim ทุก row/column
- **laws_referenced ต้องคงรายละเอียด วรรค/อนุมาตรา/(เลข) ตามที่ปรากฏในเอกสาร**
  ตัวอย่าง — ถ้าเอกสารระบุ "มาตรา ๒๙ วรรคหนึ่ง (๔)" ต้องเขียนครบทั้งสามส่วน
  ห้ามย่อเป็น "มาตรา ๒๙" เพียงอย่างเดียว
- **quality_note** เขียนเฉพาะปัญหา OCR ของตัวเอง (ภาพเบลอ ตัวอักษรไม่ชัด หน้าขาด ฯลฯ)
  ห้ามวิจารณ์เนื้อหาเอกสาร ห้าม flag เรื่องวันที่/ปี พ.ศ./ค.ศ. (ระบบจัดการให้แล้ว)
  ถ้า OCR สำเร็จไม่มีปัญหา ให้ใส่ `quality: "good"` และ `quality_note: ""`
```

Pro v2 (with rules) on ว ๒๑๐: **all 3 regressions fixed** while keeping the structural gains.

## Hybrid model design

Not all OCR phases benefit equally from Pro. For thai-legal-rag the pipeline is:

| Phase | Model used | Reason |
|---|---|---|
| classify (doc_type) | **Flash** | 6-way classification, no fidelity stake |
| extract (verbatim body) | **Pro** | Highest stakes — faithfulness + structure |
| generate_anchor (keywords + summary) | **Flash** | Term extraction + 2–3 sentences, simple |

Implemented via env-toggle (`OCR_EXTRACT_MODEL=gemini-2.5-pro` default), so rollback to Flash is one env-var change.

## Cost / latency rough numbers (Vertex AI, location=global)

- Pro extract on a 5-page Thai legal PDF: ~60s, ~7.5K tokens (~2.5K input + ~5K output)
- Flash extract on same: ~25s, ~7.5K tokens
- Pro is roughly 5–10× more expensive per token than Flash
- Tier 1 baseline (Vertex Standard PayGo, $10–$250 spend): 500K TPM → ~65 docs/min on Pro

## Watch-outs

- **Anti-summarization rules are non-negotiable for Pro**. If you take them out, Pro will silently regress. They're not "polish" — they're structural.
- **A/B compare carefully**: when reading Pro vs Flash output side-by-side, deliberately do a "what's MISSING in Pro" pass, not just "what's BETTER in Pro". Anchoring on positives first will skip negatives.
- **Cache key doesn't include model name**: `ocr.py`'s SHA256(file_id) cache will return whichever model's output was saved last. For A/B comparison you need `force=True` and side-by-side files.
- **"Smarter" is a property of the extract phase only** — classify + anchor don't show this gap, so don't blanket-assign Pro to all phases.

## Open questions for future testing

- Generalization across doc types: Pro v2 worked on ว ๒๑๐ (Circular). Need 5+ docs across Ruling_Committee, Ruling_Court before declaring rules sufficient.
- Will Pro hallucinate in `topic`/`subtopic` fields? Not tested — those have semantic latitude.
- Is there a risk of Pro consolidating sub-bullets (e.g. ๓.๑.๑ + ๓.๑.๒ → ๓.๑) when both look similar? Not seen on ว ๒๑๐ but plausible on longer docs.
