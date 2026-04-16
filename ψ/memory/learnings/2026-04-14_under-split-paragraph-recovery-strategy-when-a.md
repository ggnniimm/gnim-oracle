---
title: ## Under-Split Paragraph Recovery Strategy
tags: [thai-law, วรรค, parsing, ocr-gap, json-cache]
created: 2026-04-14
source: Thai Legal RAG 15→3 diffs fix 2026-02-21
---

# ## Under-Split Paragraph Recovery Strategy

## Under-Split Paragraph Recovery Strategy

When a parser (Gemini) under-splits legal paragraphs (got < expected), the fix is never a regex rule — it's a targeted JSON cache patch. The text structure is correct; the problem is semantic interpretation.

**Strategy**:
1. Read the full section text for all under-split sections
2. Classify: does text contain missing paragraphs, or is it genuinely truncated (OCR gap)?
3. For fixable cases: find unique substring markers at true paragraph boundaries, split at those points
4. For OCR gaps: document and accept — no parser fix can recover missing text

```python
def apply_split(paras, idx, split_at):
    p = paras[idx]
    pos = p.index(split_at)  # raises if not found — intentional
    return paras[:idx] + [p[:pos].rstrip(), p[pos:].lstrip()] + paras[idx+1:]
```

**True boundary signals in Thai law**: "ในกรณีที่...", "หลักเกณฑ์ วิธีการ...", "องค์ประกอบ องค์ประชุม...", sentence ending "ก็ได้" followed by "ในกรณีที่..."

**OCR gap signs**: section text is short relative to expected count, ends naturally (complete sentence) but Excel expects more.

---
*Added via Oracle Learn*
