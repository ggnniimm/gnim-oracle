# Rescue Phrase Post-Processing

**Date**: 2026-03-11
**Context**: Thai Legal RAG eval — TC-042 and TC-003 both failed because LLM paraphrased away critical legal phrases

## Pattern

When retrieval successfully brings chunks containing a specific phrase into the LLM context, but the LLM consistently omits or paraphrases that phrase in its answer, use post-processing to rescue the phrase.

## Implementation

```python
_RESCUE_PHRASES = [
    # (trigger_to_check_in_answer, phrase_to_find_in_chunks, sentence_to_append)
    ("ไม่ต้องรอ", "ไม่ต้องรอ", "**หมายเหตุ:** ..."),
    ("ผ่านหัวหน้าเจ้าหน้าที่", "ผ่านหัวหน้าเจ้าหน้าที่", "**หมายเหตุ:** ..."),
]

def _rescue_key_phrases(answer, chunks):
    all_text = " ".join(c.get("text", "") for c in chunks)
    for trigger, phrase, sentence in _RESCUE_PHRASES:
        if phrase in all_text and trigger not in answer:
            answer += "\n\n" + sentence
    return answer
```

## When to use

- Retrieval works (phrase is in chunks sent to LLM)
- LLM consistently paraphrases it away (not a one-off)
- The phrase is legally significant (not just stylistic)
- Prompt engineering alone doesn't fix it

## When NOT to use

- Retrieval fails (phrase not in chunks) — fix retrieval instead
- LLM sometimes includes it (flaky) — prompt engineering may suffice
- Too many rescue phrases (>10?) — rethink the approach

## Trade-offs

- Pro: Deterministic, no LLM variance
- Pro: Only fires when chunks actually contain the phrase (evidence-based)
- Con: Appends as footnote, not woven into the answer naturally
- Con: Doesn't scale well to dozens of phrases
