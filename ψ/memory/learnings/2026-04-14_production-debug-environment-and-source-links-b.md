---
title: ## Production Debug Environment and Source Links Bug
tags: [debugging, production, environment, thai-legal-rag, gemini, retry, git]
created: 2026-04-14
source: Oracle Learn
---

# ## Production Debug Environment and Source Links Bug

## Production Debug Environment and Source Links Bug

### Context
Thai Legal RAG — source links bug fix (2026-04-11), ext4 filename limit, Gemini 503 retry.

### Pattern: Always Confirm Environment Before Debugging
Ask "ทดสอบที่ localhost หรือ production?" before starting any debug investigation. 4 hours spent debugging local when problem was on production server. One question saves everything.

### Pattern: ext4 Filename Limit for Thai UTF-8
Thai characters are 3 bytes each in UTF-8. A 60-char Thai filename = 180 bytes, easily exceeding ext4's 255-byte byte limit. When transferring Thai-named files to Linux:
- Shorten filename before transfer
- Store original name in frontmatter `original_filename` field
- Use `rsync` with `--iconv` or pre-rename script

### Pattern: MMR Dedup Chunk Preference
When injecting cross-refs, verify which chunk from the same document actually gets retrieved via `--verbose`. MMR dedup picks the chunk with highest semantic similarity. In Thai legal corpus: ข้อวินิจฉัย section consistently outranks สรุปข้อวินิจฉัย. Inject into whichever section actually gets retrieved, not just the "summary" section.

### Pattern: Gemini 503 Retry with Model Fallback
```python
def generate_with_retry(prompt, model="gemini-2.5-flash"):
    for model_name in [model, "gemini-2.5-flash-lite", "gemini-2.0-flash-lite"]:
        for attempt in range(4):
            try:
                return client.generate(prompt, model=model_name)
            except (503, 429, UNAVAILABLE, RESOURCE_EXHAUSTED):
                sleep(2**attempt + random.random())
```

### Pattern: git worktree list Before Checkout
In repos with multiple worktrees (`/gnim-oracle` + `/gnim-oracle-qdrant`), `main` may already be checked out in another worktree. Always `git worktree list` before attempting checkout. Stash conflicts in append-only data files (TCs, settings) = keep both sides.

### Pattern: Script env var Must Use os.environ.get()
Scripts with hardcoded URL constants won't respect environment variable overrides. Always use `os.environ.get("QDRANT_URL", default)` — not just docstring claiming env var support.

---
*Added via Oracle Learn*
