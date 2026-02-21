# Lesson: Under-split Paragraph Recovery Strategy

**Date**: 2026-02-21
**Project**: thai-legal-rag
**Context**: Reducing วรรค paragraph count diffs from 15 → 3

---

## Pattern

When a parser (Gemini) **under-splits** legal paragraphs (got < expected), the fix is never a regex rule — it's a targeted JSON cache patch. The text structure is correct; the problem is semantic interpretation.

## Strategy

1. **Read the full section text** for all under-split sections
2. **Classify**: Does the text contain the missing paragraphs, or is it genuinely truncated (OCR gap)?
3. **For fixable cases**: find unique substring markers at true paragraph boundaries, then split the merged paragraph string at those points
4. **For OCR gaps**: document and accept — no parser fix can recover missing text

## Code Pattern

```python
def apply_split(paras, idx, split_at):
    """Split paras[idx] at the given substring marker."""
    p = paras[idx]
    pos = p.index(split_at)  # raises if not found — intentional
    part1 = p[:pos].rstrip()
    part2 = p[pos:].lstrip()
    return paras[:idx] + [part1, part2] + paras[idx+1:]
```

## Signals for True Paragraph Boundaries in Thai Law

- "ในกรณีที่..." — new conditional clause, almost always a new วรรค
- "หลักเกณฑ์  วิธีการ..." — procedural wrap-up clause, almost always a new วรรค
- "องค์ประกอบ  องค์ประชุม..." — committee rules sub-paragraph
- A sentence ending with "ก็ได้" followed by another "ในกรณีที่..." — classic วรรคสอง/สาม boundary
- Numbered list (๑)(๒)... followed by a new full sentence = two วรรค

## Robustness Validation

After manual patches, run `--resplit` (Gemini) 3× and confirm counts hold. If Gemini agrees with your patches across multiple runs, the framework is robust.

## OCR Gap Recognition

OCR truncation is the hard ceiling. Signs:
- Section text is short relative to expected วรรค count
- The text ends naturally (complete sentence) but the Excel expects more
- No amount of splitting the existing text produces the right count
