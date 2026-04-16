---
title: ## Rescue Phrase Post-Processing
tags: [post-processing, rescue-phrase, rag, generation-failure, thai-legal]
created: 2026-04-14
source: Thai Legal RAG TC-042 and TC-003 post-processing 2026-03-11
---

# ## Rescue Phrase Post-Processing

## Rescue Phrase Post-Processing

When retrieval successfully brings chunks containing a specific phrase into LLM context, but LLM consistently omits or paraphrases it, use post-processing to rescue the phrase.

```python
_RESCUE_PHRASES = [
    # (trigger_to_check_in_answer, phrase_to_find_in_chunks, sentence_to_append)
    ("ไม่ต้องรอ", "ไม่ต้องรอ", "**หมายเหตุ:** ..."),
]

def _rescue_key_phrases(answer, chunks):
    all_text = " ".join(c.get("text", "") for c in chunks)
    for trigger, phrase, sentence in _RESCUE_PHRASES:
        if phrase in all_text and trigger not in answer:
            answer += "\n\n" + sentence
    return answer
```

**When to use**: Retrieval works, LLM consistently paraphrases away, phrase is legally significant, prompt engineering alone doesn't fix it.

**When NOT to use**: Retrieval fails (fix retrieval instead), LLM sometimes includes it (prompt engineering may suffice), too many rescue phrases (>10).

**Trade-offs**: Deterministic, evidence-based (only fires when phrase in chunks). But appends as footnote, doesn't scale to dozens of phrases.

---
*Added via Oracle Learn*
